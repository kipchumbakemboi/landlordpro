from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import db
from models.payment import Payment
from models.repair import Repair
from models.notification import Notification
from services.whatsapp import whatsapp_url
from services.rent import RentCalculator

tenant_bp = Blueprint("tenant", __name__)

def tenant_required():
    if not current_user.is_authenticated or current_user.role != "tenant":
        abort(403)

def current_month_balance(tenant):
    data = RentCalculator.balance(tenant)
    return data["monthly_rent"], data["paid"], data["balance"]

def current_month_balance_detail(tenant):
    return RentCalculator.balance(tenant)

@tenant_bp.route("/dashboard")
@login_required
def dashboard():
    tenant_required()
    tenant = current_user.tenant
    rent, paid, balance = current_month_balance(tenant)
    balance_detail = current_month_balance_detail(tenant)
    repairs = Repair.query.filter_by(tenant_id=tenant.id).order_by(Repair.created_at.desc()).limit(4).all() if tenant else []
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    landlord = tenant.unit.property.landlord if tenant and tenant.unit else None
    whatsapp = whatsapp_url(landlord.phone, f"Hello {landlord.fullname}, I am {current_user.fullname} from LandlordPro.") if landlord else None
    return render_template("tenant/dashboard.html", tenant=tenant, monthly_rent=rent, paid_this_month=paid, balance=balance, late_fee=balance_detail["late_fee"], repairs=repairs, notifications=notifications, landlord=landlord, whatsapp=whatsapp)

@tenant_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    tenant_required()
    tenant = current_user.tenant
    if request.method == "POST":
        current_user.fullname = request.form.get("fullname", current_user.fullname)
        current_user.phone = request.form.get("phone", current_user.phone)
        current_user.two_factor_enabled = request.form.get("two_factor_enabled") == "on"
        if tenant:
            tenant.id_number = request.form.get("id_number", tenant.id_number)
            tenant.occupation = request.form.get("occupation", tenant.occupation)
            tenant.emergency_contact = request.form.get("emergency_contact", tenant.emergency_contact)
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("tenant.profile"))
    return render_template("tenant/profile.html", tenant=tenant)
