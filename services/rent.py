from datetime import datetime
from models import db
from models.payment import Payment

class RentCalculator:
    @staticmethod
    def month_start(dt=None):
        dt = dt or datetime.utcnow()
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def paid_this_month(tenant, dt=None):
        start = RentCalculator.month_start(dt)
        return float(db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.tenant_id == tenant.id,
            Payment.payment_date >= start,
            Payment.status == "completed",
        ).scalar() or 0)

    @staticmethod
    def late_fee(tenant, dt=None):
        dt = dt or datetime.utcnow()
        if not tenant or not tenant.unit:
            return 0.0
        rent = float(tenant.unit.rent_amount or 0)
        due_day = tenant.unit.due_day or 5
        fee_percent = float(tenant.unit.late_fee_percent or 0)
        if dt.day <= due_day:
            return 0.0
        paid = RentCalculator.paid_this_month(tenant, dt)
        if paid >= rent:
            return 0.0
        return round(rent * fee_percent / 100, 2)

    @staticmethod
    def balance(tenant, dt=None):
        if not tenant or not tenant.unit:
            return {"monthly_rent": 0.0, "paid": 0.0, "late_fee": 0.0, "balance": 0.0}
        rent = float(tenant.unit.rent_amount or 0)
        paid = RentCalculator.paid_this_month(tenant, dt)
        fee = RentCalculator.late_fee(tenant, dt)
        return {"monthly_rent": rent, "paid": paid, "late_fee": fee, "balance": max(0.0, rent + fee - paid)}
