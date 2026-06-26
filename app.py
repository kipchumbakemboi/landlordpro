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
   

app = create_app()
init_database(app)

if __name__ == "__main__":
    socketio.run(app, host="localhost", port=5000, debug=True, allow_unsafe_werkzeug=True)
