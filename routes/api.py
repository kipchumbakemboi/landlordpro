from datetime import datetime, timedelta
from functools import wraps
import jwt
from flask import Blueprint, request, jsonify, current_app
from extensions import bcrypt
from models import db
from models.user import User
from models.property import Property
from models.unit import Unit
from models.tenant import Tenant
from models.payment import Payment
from models.repair import Repair
from services.rent import RentCalculator

api_bp = Blueprint("api", __name__)

def make_token(user):
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=current_app.config["JWT_EXPIRY_HOURS"]),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")

def token_user():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        data = jwt.decode(header.split(" ", 1)[1], current_app.config["JWT_SECRET"], algorithms=["HS256"])
        return db.session.get(User, int(data["sub"]))
    except Exception:
        return None

def api_login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = token_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        request.api_user = user
        return fn(*args, **kwargs)
    return wrapper

def api_role(role):
    def dec(fn):
        @wraps(fn)
        @api_login_required
        def wrapper(*args, **kwargs):
            if request.api_user.role != role:
                return jsonify({"error": "Forbidden"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return dec

@api_bp.post("/login")
def login_api():
    data = request.get_json() or {}
    user = User.query.filter_by(email=(data.get("email") or "").lower()).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, data.get("password") or ""):
        return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({"token": make_token(user), "user": {"id": user.id, "fullname": user.fullname, "email": user.email, "role": user.role}})

@api_bp.get("/me")
@api_login_required
def me_api():
    u = request.api_user
    return jsonify({"id": u.id, "fullname": u.fullname, "email": u.email, "phone": u.phone, "role": u.role})

@api_bp.get("/landlord/dashboard")
@api_role("landlord")
def landlord_dashboard_api():
    u = request.api_user
    props = Property.query.filter_by(landlord_id=u.id).all()
    total_units = sum(p.total_units for p in props)
    occupied = sum(p.occupied_units for p in props)
    revenue = sum(float(unit.rent_amount or 0) for p in props for unit in p.units if unit.status == "occupied")
    repairs = Repair.query.join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == u.id, Repair.status != "completed").count()
    return jsonify({"properties": len(props), "total_units": total_units, "occupied_units": occupied, "vacant_units": sum(p.vacant_units for p in props), "expected_revenue": revenue, "pending_repairs": repairs})

@api_bp.get("/landlord/properties")
@api_role("landlord")
def landlord_properties_api():
    u = request.api_user
    props = Property.query.filter_by(landlord_id=u.id).all()
    return jsonify([{"id": p.id, "name": p.property_name, "location": p.location, "units": [{"id": unit.id, "number": unit.unit_number, "rent": float(unit.rent_amount), "status": unit.status} for unit in p.units]} for p in props])

@api_bp.get("/tenant/dashboard")
@api_role("tenant")
def tenant_dashboard_api():
    t = request.api_user.tenant
    if not t or not t.unit:
        return jsonify({"assigned": False})
    bal = RentCalculator.balance(t)
    return jsonify({"assigned": True, "property": t.unit.property.property_name, "unit": t.unit.unit_number, "rent": bal["monthly_rent"], "paid": bal["paid"], "late_fee": bal["late_fee"], "balance": bal["balance"]})

@api_bp.get("/payments")
@api_login_required
def payments_api():
    u = request.api_user
    if u.role == "tenant":
        q = Payment.query.filter_by(tenant_id=u.tenant.id)
    else:
        q = Payment.query.join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == u.id)
    return jsonify([{"id": p.id, "tenant": p.tenant.full_name, "unit": p.unit.unit_number, "amount": float(p.amount), "receipt": p.mpesa_receipt, "status": p.status, "date": p.payment_date.isoformat()} for p in q.order_by(Payment.payment_date.desc()).all()])

@api_bp.get("/repairs")
@api_login_required
def repairs_api():
    u = request.api_user
    if u.role == "tenant":
        q = Repair.query.filter_by(tenant_id=u.tenant.id)
    else:
        q = Repair.query.join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == u.id)
    return jsonify([{"id": r.id, "tenant": r.tenant_name, "unit": r.unit_number, "title": r.title, "priority": r.priority, "status": r.status, "created_at": r.created_at.isoformat()} for r in q.order_by(Repair.created_at.desc()).all()])

@api_bp.post("/tenant/repairs")
@api_role("tenant")
def create_repair_api():
    u = request.api_user
    data = request.get_json() or {}
    r = Repair(tenant_id=u.tenant.id, title=data.get("title"), description=data.get("description"), priority=data.get("priority", "medium"), status="pending")
    db.session.add(r)
    db.session.commit()
    return jsonify({"id": r.id, "status": r.status}), 201
