from datetime import datetime
import builtins
from . import db

class Unit(db.Model):
    __tablename__ = "units"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    unit_number = db.Column(db.String(50), nullable=False)
    rent_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    due_day = db.Column(db.Integer, default=5)
    late_fee_percent = db.Column(db.Numeric(5, 2), default=5)
    status = db.Column(db.String(20), default="vacant")  # occupied | vacant | repair
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    property = db.relationship("Property", back_populates="units")
    tenant = db.relationship("Tenant", back_populates="unit", uselist=False, lazy=True)
    payments = db.relationship("Payment", back_populates="unit", lazy=True)

    @builtins.property
    def current_rent(self):
        return float(self.rent_amount or 0)

    @builtins.property
    def tenant_name(self):
        return self.tenant.full_name if self.tenant else "Vacant"
