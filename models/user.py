from datetime import datetime
from flask_login import UserMixin
from . import db

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False, default="tenant")  # landlord | tenant
    two_factor_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    properties = db.relationship("Property", back_populates="landlord", lazy=True, cascade="all, delete-orphan")
    tenant = db.relationship("Tenant", back_populates="user", uselist=False, lazy=True, cascade="all, delete-orphan")

    @property
    def is_landlord(self):
        return self.role == "landlord"

    @property
    def is_tenant(self):
        return self.role == "tenant"

    def __repr__(self):
        return f"<User {self.email}>"
