from datetime import datetime
from . import db

class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    mpesa_receipt = db.Column(db.String(255))
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="completed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tenant = db.relationship("Tenant", back_populates="payments")
    unit = db.relationship("Unit", back_populates="payments")

    @property
    def formatted_amount(self):
        return f"KSh {float(self.amount or 0):,.2f}"
