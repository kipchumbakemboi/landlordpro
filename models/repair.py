from datetime import datetime
from . import db

class Repair(db.Model):
    __tablename__ = "repairs"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    photo = db.Column(db.String(255))
    priority = db.Column(db.String(50), default="medium")  # low | medium | high | urgent
    status = db.Column(db.String(50), default="pending")   # pending | approved | in_progress | completed
    landlord_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = db.relationship("Tenant", back_populates="repairs")

    @property
    def tenant_name(self):
        return self.tenant.full_name if self.tenant else "Unknown"

    @property
    def unit_number(self):
        return self.tenant.unit.unit_number if self.tenant and self.tenant.unit else "N/A"
