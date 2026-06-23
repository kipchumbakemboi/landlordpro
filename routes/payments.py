from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_from_directory
from flask_login import login_required, current_user
from models import db
from models.property import Property
from models.unit import Unit
from models.tenant import Tenant
from models.payment import Payment
from models.invoice import Invoice
from models.notification import Notification
from services.mpesa import MpesaService
from services.pdf_generator import generate_rent_invoice, generate_repair_invoice, UPLOAD_DIR
from services.rent import RentCalculator

payments_bp = Blueprint("payments", __name__)

def landlord_required():
    if current_user.role != "landlord":
        abort(403)

def tenant_required():
    if current_user.role != "tenant":
        abort(403)

@payments_bp.route("/landlord/payments")
@login_required
def landlord_payments():
    landlord_required()
    payments = Payment.query.join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == current_user.id).order_by(Payment.payment_date.desc()).all()
    tenants = Tenant.query.join(Unit).join(Property).filter(Property.landlord_id == current_user.id).all()
    return render_template("landlord/payments.html", payments=payments, tenants=tenants)

@payments_bp.route("/landlord/payments/record", methods=["POST"])
@login_required
def record_payment():
    landlord_required()
    tenant = Tenant.query.join(Unit).join(Property).filter(Tenant.id == int(request.form.get("tenant_id")), Property.landlord_id == current_user.id).first_or_404()
    amount = float(request.form.get("amount") or tenant.unit.rent_amount)
    receipt = request.form.get("receipt") or MpesaService().initiate_stk_push(tenant.phone, amount, tenant.unit.unit_number)["receipt"]
    payment = Payment(tenant_id=tenant.id, unit_id=tenant.unit_id, amount=amount, mpesa_receipt=receipt, payment_date=datetime.utcnow(), status="completed")
    db.session.add(payment)
    db.session.add(Notification(user_id=tenant.user_id, title="Payment Recorded", body=f"Payment of KSh {amount:,.2f} was recorded."))
    db.session.commit()
    flash(f"Payment recorded. Receipt: {receipt}", "success")
    return redirect(url_for("payments.landlord_payments"))

@payments_bp.route("/tenant/payments", methods=["GET", "POST"])
@login_required
def tenant_payments():
    tenant_required()
    tenant = current_user.tenant
    if not tenant or not tenant.unit:
        flash("No unit assigned yet.", "warning")
        return redirect(url_for("tenant.dashboard"))
    if request.method == "POST":
        amount = float(request.form.get("amount") or tenant.unit.rent_amount)
        response = MpesaService().initiate_stk_push(current_user.phone, amount, tenant.unit.unit_number)
        payment = Payment(tenant_id=tenant.id, unit_id=tenant.unit_id, amount=amount, mpesa_receipt=response.get("receipt") or response.get("checkout_request_id"), payment_date=datetime.utcnow(), status="completed" if response.get("simulated", True) else "pending")
        db.session.add(payment)
        db.session.commit()
        flash(response["message"], "success")
        return redirect(url_for("payments.tenant_payments"))
    payments = Payment.query.filter_by(tenant_id=tenant.id).order_by(Payment.payment_date.desc()).all()
    bal = RentCalculator.balance(tenant)
    invoices = Invoice.query.filter_by(tenant_id=tenant.id).order_by(Invoice.created_at.desc()).all()
    return render_template("tenant/payments.html", tenant=tenant, payments=payments, monthly_rent=bal["monthly_rent"], paid=bal["paid"], late_fee=bal["late_fee"], balance=bal["balance"], invoices=invoices)

@payments_bp.route("/invoice/generate/<int:tenant_id>")
@login_required
def generate_invoice(tenant_id):
    tenant = db.session.get(Tenant, tenant_id) or abort(404)
    if current_user.role == "tenant" and current_user.tenant.id != tenant.id:
        abort(403)
    if current_user.role == "landlord":
        Property.query.join(Unit).join(Tenant).filter(Tenant.id == tenant.id, Property.landlord_id == current_user.id).first_or_404()
    filename = generate_rent_invoice(tenant)
    invoice = Invoice(tenant_id=tenant.id, amount=float(tenant.unit.rent_amount), invoice_type="rent", pdf_path=filename)
    db.session.add(invoice)
    db.session.commit()
    return redirect(url_for("payments.download_upload", filename=filename))

@payments_bp.route("/uploads/repairs/<path:filename>")
@login_required
def download_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)

@payments_bp.route("/invoice/repair/<int:repair_id>", methods=["POST"])
@login_required
def generate_repair_invoice_route(repair_id):
    from models.repair import Repair
    repair = db.session.get(Repair, repair_id) or abort(404)
    if current_user.role == "tenant" and current_user.tenant.id != repair.tenant_id:
        abort(403)
    if current_user.role == "landlord":
        Property.query.join(Unit).join(Tenant).filter(Tenant.id == repair.tenant_id, Property.landlord_id == current_user.id).first_or_404()
    materials = float(request.form.get("materials") or 0)
    labour = float(request.form.get("labour") or 0)
    filename = generate_repair_invoice(repair, materials, labour)
    invoice = Invoice(tenant_id=repair.tenant_id, amount=materials + labour, invoice_type="repair", pdf_path=filename)
    db.session.add(invoice)
    db.session.commit()
    return redirect(url_for("payments.download_upload", filename=filename))

@payments_bp.route("/mpesa/callback", methods=["POST"])
def mpesa_callback():
    """Daraja callback endpoint.

    Updates a pending payment if a CheckoutRequestID matches mpesa_receipt.
    In simulation mode this route is not required, but production Daraja calls it.
    """
    data = request.get_json(silent=True) or {}
    stk = data.get("Body", {}).get("stkCallback", {})
    checkout_id = stk.get("CheckoutRequestID")
    result_code = stk.get("ResultCode")
    receipt = checkout_id
    amount = None
    for item in stk.get("CallbackMetadata", {}).get("Item", []):
        if item.get("Name") == "MpesaReceiptNumber":
            receipt = item.get("Value")
        if item.get("Name") == "Amount":
            amount = item.get("Value")
    payment = Payment.query.filter_by(mpesa_receipt=checkout_id).first() if checkout_id else None
    if payment:
        payment.status = "completed" if result_code == 0 else "failed"
        payment.mpesa_receipt = receipt
        if amount:
            payment.amount = amount
        db.session.commit()
    return {"ResultCode": 0, "ResultDesc": "Accepted"}
