from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import random
from extensions import bcrypt
from models import db
from models.user import User
from models.tenant import Tenant
from services.notification_service import notification_service

INDEX_REDIRECT = {
    "landlord": "landlord.dashboard",
    "tenant": "tenant.dashboard",
}

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

def _reset_token(user):
    return _serializer().dumps({"uid": user.id}, salt="password-reset")

def _verify_reset_token(token, max_age=3600):
    try:
        data = _serializer().loads(token, salt="password-reset", max_age=max_age)
        return db.session.get(User, data["uid"])
    except (BadSignature, SignatureExpired, KeyError):
        return None

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(INDEX_REDIRECT.get(current_user.role, "index")))
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "tenant")
        if not fullname or not email or not password:
            flash("Full name, email and password are required.", "danger")
            return render_template("auth/register.html")
        if role not in ["landlord", "tenant"]:
            role = "tenant"
        if User.query.filter_by(email=email).first():
            flash("That email already exists. Please login.", "warning")
            return redirect(url_for("auth.login"))
        user = User(fullname=fullname, email=email, phone=phone, role=role, password_hash=bcrypt.generate_password_hash(password).decode("utf-8"))
        db.session.add(user)
        db.session.commit()
        if role == "tenant":
            tenant = Tenant(
                user_id=user.id,
                id_number=request.form.get("id_number"),
                occupation=request.form.get("occupation"),
                emergency_contact=request.form.get("emergency_contact"),
                approved=False,
            )
            db.session.add(tenant)
            db.session.commit()
        flash("Account created successfully. You can now login.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(INDEX_REDIRECT.get(current_user.role, "index")))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            if user.two_factor_enabled:
                code = f"{random.randint(100000, 999999)}"
                session["pending_2fa_user"] = user.id
                session["pending_2fa_code"] = code
                notification_service.send_email(user.email, "LandlordPro 2FA Code", f"Your LandlordPro verification code is {code}.")
                notification_service.send_sms(user.phone, f"LandlordPro code: {code}")
                flash("A 2FA code has been sent to your configured email/SMS. In local development check the server logs.", "info")
                return redirect(url_for("auth.two_factor"))
            login_user(user)
            flash(f"Welcome back, {user.fullname.split()[0]}!", "success")
            return redirect(url_for(INDEX_REDIRECT.get(user.role, "index")))
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html")

@auth_bp.route("/2fa", methods=["GET", "POST"])
def two_factor():
    uid = session.get("pending_2fa_user")
    if not uid:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        if request.form.get("code") == session.get("pending_2fa_code"):
            user = db.session.get(User, uid)
            session.pop("pending_2fa_user", None)
            session.pop("pending_2fa_code", None)
            login_user(user)
            flash("2FA verified.", "success")
            return redirect(url_for(INDEX_REDIRECT.get(user.role, "index")))
        flash("Invalid or expired code.", "danger")
    return render_template("auth/2fa.html")

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = _reset_token(user)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            notification_service.send_email(user.email, "LandlordPro Password Reset", f"Reset your password here: {reset_url}\nThis link expires in 1 hour.")
            current_app.logger.info("Password reset link for %s: %s", user.email, reset_url)
        flash("If that email exists, a reset link has been sent. In local development check the server logs.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html")

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = _verify_reset_token(token)
    if not user:
        flash("Reset link is invalid or expired.", "danger")
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if len(password) < 6 or password != confirm:
            flash("Password must be at least 6 characters and match confirmation.", "danger")
            return render_template("auth/reset_password.html")
        user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        db.session.commit()
        flash("Password reset successfully. Please login.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))
