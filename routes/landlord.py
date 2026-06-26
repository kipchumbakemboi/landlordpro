from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from extensions import bcrypt
from models import db
from models.user import User
from models.property import Property
from models.unit import Unit
from models.tenant import Tenant
from models.payment import Payment
from models.repair import Repair
from models.notification import Notification
from services.rent import RentCalculator
from werkzeug.utils import secure_filename
import os

landlord_bp = Blueprint("landlord", __name__)


def _date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except ValueError:
        return None

def _lease_upload(user_id):
    file = request.files.get("lease_document")
    if file and file.filename:
        name = f"lease_{user_id}_{datetime.utcnow():%Y%m%d%H%M%S}_{secure_filename(file.filename)}"
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], name))
        return name
    return None

def landlord_required():
    if not current_user.is_authenticated or current_user.role != "landlord":
        abort(403)

def landlord_properties():
    return Property.query.filter_by(landlord_id=current_user.id).all()

def landlord_stats():
    properties = landlord_properties()
    total_units = sum(p.total_units for p in properties)
    occupied_units = sum(p.occupied_units for p in properties)
    vacant_units = sum(p.vacant_units for p in properties)
    repair_units = sum(p.repair_units for p in properties)
    expected_revenue = sum(float(u.rent_amount or 0) for p in properties for u in p.units if u.status == "occupied")
    start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    collected = db.session.query(db.func.sum(Payment.amount)).join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == current_user.id, Payment.payment_date >= start, Payment.status == "completed").scalar() or 0
    pending_repairs = Repair.query.join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == current_user.id, Repair.status.in_(["pending", "approved", "in_progress"])).count()
    tenant_count = Tenant.query.join(Unit).join(Property).filter(Property.landlord_id == current_user.id, Tenant.approved == True).count()
    occupancy_rate = round((occupied_units / total_units * 100), 1) if total_units else 0
    outstanding = sum(RentCalculator.balance(t)["balance"] for t in Tenant.query.join(Unit).join(Property).filter(Property.landlord_id == current_user.id).all())
    return dict(properties=properties, total_units=total_units, occupied_units=occupied_units, vacant_units=vacant_units, repair_units=repair_units, expected_revenue=expected_revenue, collected_this_month=float(collected), pending_repairs=pending_repairs, tenant_count=tenant_count, occupancy_rate=occupancy_rate, outstanding=outstanding)

@landlord_bp.route("/dashboard")
@login_required
def dashboard():
    landlord_required()
    stats = landlord_stats()
    recent_payments = Payment.query.join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == current_user.id).order_by(Payment.payment_date.desc()).limit(6).all()
    recent_repairs = Repair.query.join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == current_user.id).order_by(Repair.created_at.desc()).limit(6).all()
    return render_template("landlord/dashboard.html", **stats, recent_payments=recent_payments, recent_repairs=recent_repairs)

@landlord_bp.route("/properties")
@login_required
def properties():
    landlord_required()
    return render_template("landlord/properties.html", properties=landlord_properties())

@landlord_bp.route("/properties/add", methods=["POST"])
@login_required
def add_property():
    landlord_required()
    name = request.form.get("property_name", "").strip()
    location = request.form.get("location", "").strip()
    if not name:
        flash("Property name is required.", "danger")
        return redirect(url_for("landlord.properties"))
    db.session.add(Property(landlord_id=current_user.id, property_name=name, location=location))
    db.session.commit()
    flash("Property added successfully.", "success")
    return redirect(url_for("landlord.properties"))

@landlord_bp.route("/properties/<int:property_id>/delete", methods=["POST"])
@login_required
def delete_property(property_id):
    landlord_required()
    prop = Property.query.filter_by(id=property_id, landlord_id=current_user.id).first_or_404()
    db.session.delete(prop)
    db.session.commit()
    flash("Property deleted.", "info")
    return redirect(url_for("landlord.properties"))

@landlord_bp.route("/properties/<int:property_id>/units/add", methods=["POST"])
@login_required
def add_unit(property_id):
    landlord_required()
    prop = Property.query.filter_by(id=property_id, landlord_id=current_user.id).first_or_404()
    unit_number = request.form.get("unit_number", "").strip()
    rent_amount = float(request.form.get("rent_amount") or 0)
    due_day = int(request.form.get("due_day") or 5)
    status = request.form.get("status") or "vacant"
    late_fee_percent = float(request.form.get("late_fee_percent") or 5)
    if status not in ["occupied", "vacant", "repair"]:
        status = "vacant"
    if not unit_number or rent_amount <= 0:
        flash("Unit number and rent amount are required.", "danger")
        return redirect(url_for("landlord.properties"))
    db.session.add(Unit(property_id=prop.id, unit_number=unit_number, rent_amount=rent_amount, due_day=due_day, late_fee_percent=late_fee_percent, status=status))
    db.session.commit()
    flash("Unit added.", "success")
    return redirect(url_for("landlord.properties"))

@landlord_bp.route("/units/<int:unit_id>/status", methods=["POST"])
@login_required
def update_unit_status(unit_id):
    landlord_required()
    unit = Unit.query.join(Property).filter(Unit.id == unit_id, Property.landlord_id == current_user.id).first_or_404()
    status = request.form.get("status", "vacant")
    if status in ["occupied", "vacant", "repair"]:
        unit.status = status
        db.session.commit()
        flash("Unit status updated.", "success")
    return redirect(url_for("landlord.properties"))

@landlord_bp.route("/tenants")
@login_required
def tenants():
    landlord_required()
    assigned_tenants = Tenant.query.join(Unit).join(Property).filter(Property.landlord_id == current_user.id).order_by(Tenant.created_at.desc()).all()
    pending_tenants = Tenant.query.filter(Tenant.unit_id.is_(None)).order_by(Tenant.created_at.desc()).all()
    vacant_units = Unit.query.join(Property).filter(Property.landlord_id == current_user.id, Unit.status.in_(["vacant", "repair"])).all()
    return render_template("landlord/tenants.html", tenants=assigned_tenants, pending_tenants=pending_tenants, vacant_units=vacant_units)


@landlord_bp.route("/tenants/add", methods=["POST"])
@login_required
def add_tenant():
    landlord_required()

    email = request.form.get("email", "").strip().lower()
    fullname = request.form.get("fullname", "").strip()
    phone = request.form.get("phone", "").strip()
    unit_id = request.form.get("unit_id") or None
    password = request.form.get("password", "")

    if not fullname or not email or len(password) < 6:
        flash("Full name, email, and a password of at least 6 characters are required.", "danger")
        return redirect(url_for("landlord.tenants"))

    if User.query.filter_by(email=email).first():
        flash("A user with that email already exists.", "warning")
        return redirect(url_for("landlord.tenants"))

    user = User(
        fullname=fullname,
        email=email,
        phone=phone,
        role="tenant",
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8")
    )

    db.session.add(user)
    db.session.commit()

    tenant = Tenant(
        user_id=user.id,
        unit_id=unit_id,
        id_number=request.form.get("id_number"),
        occupation=request.form.get("occupation"),
        emergency_contact=request.form.get("emergency_contact"),
        lease_start=_date(request.form.get("lease_start")),
        lease_end=_date(request.form.get("lease_end")),
        lease_document=_lease_upload(user.id),
        approved=True
    )

    db.session.add(tenant)

    if unit_id:
        unit = db.session.get(Unit, int(unit_id))
        unit.status = "occupied"

    db.session.commit()

    flash("Tenant added successfully.", "success")
    return redirect(url_for("landlord.tenants"))


@landlord_bp.route("/tenants/<int:tenant_id>/assign", methods=["POST"])
@login_required
def assign_tenant(tenant_id):
    landlord_required()

    tenant = db.session.get(Tenant, tenant_id) or abort(404)

    unit_id = request.form.get("unit_id")
    if not unit_id:
        flash("Please select a unit to assign.", "danger")
        return redirect(url_for("landlord.tenants"))

    unit = Unit.query.join(Property).filter(
        Unit.id == int(unit_id),
        Property.landlord_id == current_user.id
    ).first_or_404()

    if tenant.unit:
        tenant.unit.status = "vacant"

    tenant.unit_id = unit.id
    tenant.approved = True
    tenant.lease_start = _date(request.form.get("lease_start")) or tenant.lease_start
    tenant.lease_end = _date(request.form.get("lease_end")) or tenant.lease_end
    tenant.lease_document = _lease_upload(tenant.user_id) or tenant.lease_document

    unit.status = "occupied"

    db.session.commit()

    flash("Tenant assigned and approved successfully.", "success")
    return redirect(url_for("landlord.tenants"))

@landlord_bp.route("/tenants/<int:tenant_id>/approve", methods=["POST"])
@login_required
def approve_tenant(tenant_id):
    landlord_required()
    tenant = db.session.get(Tenant, tenant_id) or abort(404)
    tenant.approved = True
    db.session.commit()
    flash("Tenant approved. Assign a unit when ready.", "success")
    return redirect(url_for("landlord.tenants"))


@landlord_bp.route("/reminders/send", methods=["POST"])
@login_required
def send_rent_reminders():
    landlord_required()
    from services.notification_service import notification_service
    tenants = Tenant.query.join(Unit).join(Property).filter(Property.landlord_id == current_user.id).all()
    sent = 0
    for tenant in tenants:
        bal = RentCalculator.balance(tenant)
        if bal["balance"] > 0:
            msg = f"Dear {tenant.full_name}, your LandlordPro rent balance for Unit {tenant.unit.unit_number} is KSh {bal['balance']:,.2f}. Kindly pay before/at your due date."
            notification_service.send_email(tenant.email, "Rent Reminder", msg)
            notification_service.send_sms(tenant.phone, msg)
            db.session.add(Notification(user_id=tenant.user_id, title="Rent Reminder", body=msg))
            sent += 1
    db.session.commit()
    flash(f"Rent reminders sent to {sent} tenant(s).", "success")
    return redirect(url_for("landlord.dashboard"))

@landlord_bp.route("/invoices/monthly", methods=["POST"])
@login_required
def generate_monthly_invoices():
    landlord_required()
    from models.invoice import Invoice
    from services.pdf_generator import generate_rent_invoice
    tenants = Tenant.query.join(Unit).join(Property).filter(Property.landlord_id == current_user.id).all()
    count = 0
    for tenant in tenants:
        bal = RentCalculator.balance(tenant)
        filename = generate_rent_invoice(tenant, bal["balance"])
        if filename:
            db.session.add(Invoice(tenant_id=tenant.id, amount=bal["balance"], invoice_type="rent", pdf_path=filename))
            count += 1
    db.session.commit()
    flash(f"Generated {count} monthly rent invoice(s).", "success")
    return redirect(url_for("payments.landlord_payments"))

