from datetime import datetime
from . import db

class Tenant(db.Model):
    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=True)
    id_number = db.Column(db.String(50))
    occupation = db.Column(db.String(120))
    emergency_contact = db.Column(db.String(120))
    lease_start = db.Column(db.Date)
    lease_end = db.Column(db.Date)
    lease_document = db.Column(db.String(255))
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="tenant")
    unit = db.relationship("Unit", back_populates="tenant")
    payments = db.relationship("Payment", back_populates="tenant", lazy=True, cascade="all, delete-orphan")
    repairs = db.relationship("Repair", back_populates="tenant", lazy=True, cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", back_populates="tenant", lazy=True, cascade="all, delete-orphan")

    @property
    def full_name(self):
        return self.user.fullname if self.user else "Unknown Tenant"

    @property
    def email(self):
        return self.user.email if self.user else ""

    @property
    def phone(self):
        return self.user.phone if self.user else ""
