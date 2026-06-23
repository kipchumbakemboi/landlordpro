from datetime import datetime
from . import db

class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    invoice_type = db.Column(db.String(100), default="rent")
    pdf_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tenant = db.relationship("Tenant", back_populates="invoices")
