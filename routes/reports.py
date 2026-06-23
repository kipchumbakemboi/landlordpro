from datetime import datetime
from io import BytesIO
from flask import Blueprint, render_template, redirect, url_for, abort, send_file, request
from flask_login import login_required, current_user
from openpyxl import Workbook
from models import db
from models.property import Property
from models.unit import Unit
from models.tenant import Tenant
from models.payment import Payment
from models.repair import Repair
from services.pdf_generator import generate_report_pdf, UPLOAD_DIR

reports_bp = Blueprint("reports", __name__)

def require_landlord():
    if current_user.role != "landlord":
        abort(403)

def _range():
    try:
        start = datetime.strptime(request.args.get("start", ""), "%Y-%m-%d") if request.args.get("start") else None
        end = datetime.strptime(request.args.get("end", ""), "%Y-%m-%d") if request.args.get("end") else None
        if end:
            end = end.replace(hour=23, minute=59, second=59)
        return start, end
    except ValueError:
        return None, None

def report_rows(report_type):
    start, end = _range()
    if report_type == "occupancy":
        props = Property.query.filter_by(landlord_id=current_user.id).all()
        return [{"Property": p.property_name, "Location": p.location or "", "Units": p.total_units, "Occupied": p.occupied_units, "Vacant": p.vacant_units, "Under Repair": p.repair_units, "Rate": f"{round(p.occupied_units / p.total_units * 100, 1) if p.total_units else 0}%"} for p in props]
    if report_type == "revenue":
        rows = []
        units = Unit.query.join(Property).filter(Property.landlord_id == current_user.id).all()
        for u in units:
            pq = db.session.query(db.func.sum(Payment.amount)).filter(Payment.unit_id == u.id, Payment.status == "completed")
            if start:
                pq = pq.filter(Payment.payment_date >= start)
            if end:
                pq = pq.filter(Payment.payment_date <= end)
            paid = pq.scalar() or 0
            rows.append({"Property": u.property.property_name, "Unit": u.unit_number, "Tenant": u.tenant.full_name if u.tenant else "Vacant", "Monthly Rent": float(u.rent_amount), "Total Paid": float(paid), "Status": u.status})
        return rows
    if report_type == "repairs":
        rq = Repair.query.join(Tenant).join(Unit).join(Property).filter(Property.landlord_id == current_user.id)
        if start:
            rq = rq.filter(Repair.created_at >= start)
        if end:
            rq = rq.filter(Repair.created_at <= end)
        repairs = rq.all()
        return [{"Unit": r.unit_number, "Tenant": r.tenant_name, "Issue": r.title, "Priority": r.priority, "Status": r.status, "Date": r.created_at.strftime("%Y-%m-%d")} for r in repairs]
    abort(404)

def report_summary(rows):
    return {"Records": len(rows), "Generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M")}

@reports_bp.route("/landlord/reports")
@login_required
def landlord_reports():
    require_landlord()
    occupancy = report_rows("occupancy")
    revenue = report_rows("revenue")
    repairs = report_rows("repairs")
    total_units = sum(int(r["Units"]) for r in occupancy)
    occupied = sum(int(r["Occupied"]) for r in occupancy)
    monthly_expected = sum(float(r["Monthly Rent"]) for r in revenue if r["Status"] == "occupied")
    total_paid = sum(float(r["Total Paid"]) for r in revenue)
    return render_template("landlord/reports.html", occupancy=occupancy, revenue=revenue, repairs=repairs, total_units=total_units, occupied=occupied, occupancy_rate=round(occupied / total_units * 100, 1) if total_units else 0, monthly_expected=monthly_expected, total_paid=total_paid, start=request.args.get("start", ""), end=request.args.get("end", ""))

@reports_bp.route("/landlord/reports/<report_type>/pdf")
@login_required
def export_pdf(report_type):
    require_landlord()
    rows = report_rows(report_type)
    filename = generate_report_pdf(current_user, report_type, rows, report_summary(rows))
    return redirect(url_for("payments.download_upload", filename=filename))

@reports_bp.route("/landlord/reports/<report_type>/excel")
@login_required
def export_excel(report_type):
    require_landlord()
    rows = report_rows(report_type)
    wb = Workbook()
    ws = wb.active
    ws.title = report_type.title()
    if rows:
        ws.append(list(rows[0].keys()))
        for row in rows:
            ws.append(list(row.values()))
    else:
        ws.append(["No records"])
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return send_file(stream, as_attachment=True, download_name=f"landlordpro_{report_type}_{datetime.utcnow():%Y%m%d}.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
