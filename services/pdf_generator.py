import os
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads", "repairs"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _doc(filename):
    return SimpleDocTemplate(os.path.join(UPLOAD_DIR, filename), pagesize=A4, rightMargin=45, leftMargin=45, topMargin=40, bottomMargin=40)

def generate_rent_invoice(tenant, balance=None):
    if not tenant or not tenant.unit:
        return None
    amount = float(balance if balance is not None else tenant.unit.rent_amount)
    filename = f"invoice_rent_{tenant.id}_{datetime.now():%Y%m%d%H%M%S}.pdf"
    doc = _doc(filename)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Heading1"], alignment=TA_CENTER, textColor=colors.HexColor("#2563eb"), fontSize=22)
    small_center = ParagraphStyle("small_center", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9, textColor=colors.grey)
    elements = [
        Paragraph("LANDLORDPRO", title),
        Paragraph("Official Rent Invoice", small_center),
        Spacer(1, 20),
        Paragraph(f"<b>Tenant:</b> {tenant.full_name}", styles["Normal"]),
        Paragraph(f"<b>Unit:</b> {tenant.unit.unit_number}", styles["Normal"]),
        Paragraph(f"<b>Property:</b> {tenant.unit.property.property_name}", styles["Normal"]),
        Paragraph(f"<b>Landlord:</b> {tenant.unit.property.landlord.fullname}", styles["Normal"]),
        Spacer(1, 15),
    ]
    due = datetime.now().replace(day=min(tenant.unit.due_day or 5, 28))
    if due < datetime.now():
        due += timedelta(days=30)
    data = [
        ["Description", "Amount"],
        [f"Monthly Rent - {datetime.now():%B %Y}", f"KSh {float(tenant.unit.rent_amount):,.2f}"],
        ["Outstanding Balance", f"KSh {amount:,.2f}"],
        ["Due Date", due.strftime("%Y-%m-%d")],
        ["Total Due", f"KSh {amount:,.2f}"],
    ]
    table = Table(data, colWidths=[310, 160])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("PADDING", (0,0), (-1,-1), 8),
    ]))
    elements += [table, Spacer(1, 20), Paragraph("Payment: M-Pesa Paybill 123456, Account = Unit Number", styles["Normal"]), Spacer(1, 25), Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M}", small_center)]
    doc.build(elements)
    return filename

def generate_report_pdf(landlord, report_type, rows, summary):
    filename = f"report_{report_type}_{landlord.id}_{datetime.now():%Y%m%d%H%M%S}.pdf"
    doc = _doc(filename)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Heading1"], alignment=TA_CENTER, textColor=colors.HexColor("#2563eb"), fontSize=20)
    elements = [Paragraph("LANDLORDPRO", title), Paragraph(f"{report_type.title()} Report", styles["Heading2"]), Paragraph(f"Landlord: {landlord.fullname}", styles["Normal"]), Paragraph(f"Generated: {datetime.now():%Y-%m-%d}", styles["Normal"]), Spacer(1, 12)]
    if summary:
        elements.append(Paragraph("Summary", styles["Heading3"]))
        for k, v in summary.items():
            elements.append(Paragraph(f"<b>{k}:</b> {v}", styles["Normal"]))
        elements.append(Spacer(1, 12))
    if rows:
        headers = list(rows[0].keys())
        data = [headers] + [[str(row.get(h, "")) for h in headers] for row in rows]
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("PADDING", (0,0), (-1,-1), 5),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No records found for this report.", styles["Normal"]))
    doc.build(elements)
    return filename

def generate_repair_invoice(repair, materials=0, labour=0):
    """Generate a PDF invoice for a completed repair."""
    tenant = repair.tenant
    materials = float(materials or 0)
    labour = float(labour or 0)
    total = materials + labour
    filename = f"invoice_repair_{repair.id}_{datetime.now():%Y%m%d%H%M%S}.pdf"
    doc = _doc(filename)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title_repair", parent=styles["Heading1"], alignment=TA_CENTER, textColor=colors.HexColor("#2563eb"), fontSize=22)
    elements = [
        Paragraph("LANDLORDPRO", title),
        Paragraph("Repair Invoice", styles["Heading2"]),
        Spacer(1, 15),
        Paragraph(f"<b>Tenant:</b> {tenant.full_name}", styles["Normal"]),
        Paragraph(f"<b>Unit:</b> {tenant.unit.unit_number if tenant.unit else 'N/A'}", styles["Normal"]),
        Paragraph(f"<b>Repair:</b> {repair.title}", styles["Normal"]),
        Paragraph(f"<b>Status:</b> {repair.status.replace('_', ' ').title()}", styles["Normal"]),
        Spacer(1, 15),
    ]
    data = [["Item", "Cost"], ["Materials", f"KSh {materials:,.2f}"], ["Labour", f"KSh {labour:,.2f}"], ["Total", f"KSh {total:,.2f}"]]
    table = Table(data, colWidths=[310, 160])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#dbeafe")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("PADDING", (0,0), (-1,-1), 8),
    ]))
    elements += [table, Spacer(1, 20), Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M}", styles["Normal"])]
    doc.build(elements)
    return filename
