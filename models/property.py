from datetime import datetime
from . import db

class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    landlord_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    property_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    landlord = db.relationship("User", back_populates="properties")
    units = db.relationship("Unit", back_populates="property", lazy=True, cascade="all, delete-orphan")

    @property
    def total_units(self):
        return len(self.units)

    @property
    def occupied_units(self):
        return sum(1 for unit in self.units if unit.status == "occupied")

    @property
    def vacant_units(self):
        return sum(1 for unit in self.units if unit.status == "vacant")

    @property
    def repair_units(self):
        return sum(1 for unit in self.units if unit.status == "repair")
