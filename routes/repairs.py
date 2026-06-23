from datetime import datetime
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db
from models.property import Property
from models.unit import Unit
from models.tenant import Tenant
from models.repair import Repair
from models.notification import Notification

repairs_bp = Blueprint("repairs", __name__)

ALLOWED = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED

@repairs_bp.route("/tenant/repairs", methods=["GET", "POST"])
@login_required
def tenant_repairs():
    if current_user.role != "tenant":
        abort(403)
    tenant = current_user.tenant
    if not tenant:
        flash("Tenant profile missing.", "warning")
        return redirect(url_for("tenant.dashboard"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "medium")
        if not title:
            flash("Repair title is required.", "danger")
            return redirect(url_for("repairs.tenant_repairs"))
        photo_name = None
        file = request.files.get("photo")
        if file and file.filename and allowed_file(file.filename):
            safe = secure_filename(file.filename)
            photo_name = f"repair_{tenant.id}_{datetime.utcnow():%Y%m%d%H%M%S}_{safe}"
            file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], photo_name))
        repair = Repair(tenant_id=tenant.id, title=title, description=description, priority=priority, photo=photo_name, status="pending")
        db.session.add(repair)
        if tenant.unit and tenant.unit.property:
            db.session.add(Notification(user_id=tenant.unit.property.landlord_id, title="New Repair Request", body=f"{tenant.full_name}: {title}"))
        db.session.commit()
        flash("Maintenance request submitted.", "success")
        return redirect(url_for("repairs.tenant_repairs"))
    repairs = Repair.query.filter_by(tenant_id=tenant.id).order_by(Repair.created_at.desc()).all()
    return render_template("tenant/repairs.html", tenant=tenant, repairs=repairs)

@repairs_bp.route("/landlord/repairs")
@login_required
def landlord_repairs():
    if current_user.role != "landlord":
        abort(403)
    repairs = Repair.query.join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == current_user.id).order_by(Repair.created_at.desc()).all()
    return render_template("landlord/repairs.html", repairs=repairs)

@repairs_bp.route("/landlord/repairs/<int:repair_id>/update", methods=["POST"])
@login_required
def update_repair(repair_id):
    if current_user.role != "landlord":
        abort(403)
    repair = Repair.query.join(Tenant).join(Unit).join(Property).filter(Repair.id == repair_id, Property.landlord_id == current_user.id).first_or_404()
    status = request.form.get("status")
    if status in ["pending", "approved", "in_progress", "completed"]:
        repair.status = status
    repair.landlord_note = request.form.get("landlord_note", repair.landlord_note)
    db.session.add(Notification(user_id=repair.tenant.user_id, title="Repair Updated", body=f"{repair.title} is now {repair.status.replace('_', ' ')}."))
    db.session.commit()
    flash("Repair status updated.", "success")
    return redirect(url_for("repairs.landlord_repairs"))
