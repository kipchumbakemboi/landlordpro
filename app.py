from datetime import datetime, timedelta
from flask import Flask
from config import config
from models import db
from models.user import User
from models.property import Property
from models.unit import Unit
from models.tenant import Tenant
from models.payment import Payment
from models.repair import Repair
from models.invoice import Invoice
from models.message import Message
from models.notification import Notification

from extensions import bcrypt, login_manager, migrate, mail, socketio

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    socketio.init_app(app)

    from routes.auth import auth_bp
    from routes.landlord import landlord_bp
    from routes.tenant import tenant_bp
    from routes.payments import payments_bp
    from routes.repairs import repairs_bp
    from routes.reports import reports_bp
    from routes.chatbot import chatbot_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(landlord_bp, url_prefix="/landlord")
    app.register_blueprint(tenant_bp, url_prefix="/tenant")
    app.register_blueprint(payments_bp)
    app.register_blueprint(repairs_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    @app.route("/")
    def index():
        from flask import render_template
        return render_template("index.html")

    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow()}

    return app

def seed_demo_data():
    if User.query.count() > 0:
        return
    landlord = User(
        fullname="Chrispus Tanui",
        email="landlord@landlordpro.com",
        phone="+254712345678",
        password_hash=bcrypt.generate_password_hash("password123").decode("utf-8"),
        role="landlord",
    )
    tenant_user = User(
        fullname="Obadiah Kipchumba",
        email="tenant@landlordpro.com",
        phone="+2547123456789",
        password_hash=bcrypt.generate_password_hash("password123").decode("utf-8"),
        role="tenant",
    )
    tenant2_user = User(
        fullname="Kelvin Sirma",
        email="kelvin@landlordpro.com",
        phone="+2547023456789",
        password_hash=bcrypt.generate_password_hash("password123").decode("utf-8"),
        role="tenant",
    )
    db.session.add_all([landlord, tenant_user, tenant2_user])
    db.session.commit()

    prop1 = Property(landlord_id=landlord.id, property_name="Sunrise Apartments", location="Kilimani, Nairobi")
    prop2 = Property(landlord_id=landlord.id, property_name="Green View Court", location="Westlands, Nairobi")
    db.session.add_all([prop1, prop2])
    db.session.commit()

    units = [
        Unit(property_id=prop1.id, unit_number="A1", rent_amount=25000, due_day=5, status="occupied"),
        Unit(property_id=prop1.id, unit_number="A2", rent_amount=22000, due_day=5, status="vacant"),
        Unit(property_id=prop1.id, unit_number="A3", rent_amount=28000, due_day=5, status="repair"),
        Unit(property_id=prop2.id, unit_number="B1", rent_amount=35000, due_day=3, status="occupied"),
    ]
    db.session.add_all(units)
    db.session.commit()

    tenant1 = Tenant(
        user_id=tenant_user.id,
        unit_id=units[0].id,
        id_number="12345678",
        occupation="Teacher",
        emergency_contact="+254700111222",
        lease_start=datetime.utcnow().date() - timedelta(days=180),
        lease_end=datetime.utcnow().date() + timedelta(days=185),
        approved=True,
    )
    tenant2 = Tenant(
        user_id=tenant2_user.id,
        unit_id=units[3].id,
        id_number="87654321",
        occupation="Software Developer",
        emergency_contact="+254733444555",
        lease_start=datetime.utcnow().date() - timedelta(days=40),
        lease_end=datetime.utcnow().date() + timedelta(days=325),
        approved=True,
    )
    db.session.add_all([tenant1, tenant2])
    db.session.commit()

    payments = [
        Payment(tenant_id=tenant1.id, unit_id=units[0].id, amount=25000, mpesa_receipt="LP06010001", payment_date=datetime.utcnow() - timedelta(days=22), status="completed"),
        Payment(tenant_id=tenant1.id, unit_id=units[0].id, amount=25000, mpesa_receipt="LP05010002", payment_date=datetime.utcnow() - timedelta(days=53), status="completed"),
        Payment(tenant_id=tenant2.id, unit_id=units[3].id, amount=20000, mpesa_receipt="LP06010003", payment_date=datetime.utcnow() - timedelta(days=9), status="completed"),
    ]
    repairs = [
        Repair(tenant_id=tenant1.id, title="Leaking Kitchen Tap", description="The kitchen tap has been dripping for three days.", priority="medium", status="pending"),
        Repair(tenant_id=tenant2.id, title="Electrical Fault", description="Socket near the TV sparks when switched on.", priority="urgent", status="approved"),
        Repair(tenant_id=tenant1.id, title="Broken Window Lock", description="Bedroom window lock needs replacement.", priority="high", status="completed"),
    ]
    messages = [
        Message(sender_id=landlord.id, receiver_id=tenant_user.id, content="Hello Mary, rent is due on the 5th. Kindly confirm once paid."),
        Message(sender_id=tenant_user.id, receiver_id=landlord.id, content="Thanks John. I will pay today."),
    ]
    notifications = [
        Notification(user_id=tenant_user.id, title="Welcome to LandlordPro", body="Your tenant dashboard is ready."),
        Notification(user_id=landlord.id, title="New maintenance request", body="Mary submitted a leaking tap request."),
    ]
    db.session.add_all(payments + repairs + messages + notifications)
    db.session.commit()


def ensure_schema_upgrades():
    """Small SQLite-safe schema upgrades for prototype evolution.

    Flask-Migrate is configured for production migrations; this helper keeps
    the existing local SQLite demo database working after new columns are added.
    """
    if not db.engine.url.drivername.startswith("sqlite"):
        return
    with db.engine.begin() as conn:
        def cols(table):
            return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
        unit_cols = cols("units")
        if "late_fee_percent" not in unit_cols:
            conn.exec_driver_sql("ALTER TABLE units ADD COLUMN late_fee_percent NUMERIC(5, 2) DEFAULT 5")
        tenant_cols = cols("tenants")
        if "lease_document" not in tenant_cols:
            conn.exec_driver_sql("ALTER TABLE tenants ADD COLUMN lease_document VARCHAR(255)")

def init_database(app):
    with app.app_context():
        db.create_all()
        ensure_schema_upgrades()
        seed_demo_data()

app = create_app()
init_database(app)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)
