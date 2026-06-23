from flask import current_app

class LandlordProAI:
    """AI assistant. Uses OpenAI if configured, otherwise a robust rule-based fallback."""

    def _openai_answer(self, user, question, stats, tenant):
        api_key = current_app.config.get("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            context = {
                "role": user.role,
                "name": user.fullname,
                "stats": stats,
                "tenant_unit": tenant.unit.unit_number if tenant and tenant.unit else None,
                "tenant_property": tenant.unit.property.property_name if tenant and tenant.unit else None,
            }
            prompt = (
                "You are LandlordPro's property management assistant. "
                "Answer concisely using the supplied database context. "
                f"Context: {context}\nQuestion: {question}"
            )
            response = client.chat.completions.create(
                model=current_app.config.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            current_app.logger.info("OpenAI fallback: %s", exc)
            return None

    def answer(self, user, question, stats=None, tenant=None):
        q = (question or "").lower()
        stats = stats or {}
        if not q.strip():
            return "Please type a question about rent, payments, repairs, units, occupancy, or revenue."
        live = self._openai_answer(user, question, stats, tenant)
        if live:
            return live

        if user.role == "tenant":
            if not tenant or not tenant.unit:
                return "Your account is active, but no unit has been assigned yet. Please contact your landlord."
            rent = float(tenant.unit.rent_amount or 0)
            if any(word in q for word in ["balance", "rent", "owe", "due", "pay", "penalty", "late"]):
                return f"Your monthly rent for Unit {tenant.unit.unit_number} is KSh {rent:,.2f}. Balance including any late fee is KSh {stats.get('balance', 0):,.2f}."
            if any(word in q for word in ["repair", "maintenance", "broken", "leak", "electric"]):
                return "Go to Repairs, add the issue title, priority, description, and upload a photo. Your landlord will see it instantly."
            if "invoice" in q or "receipt" in q:
                return "You can generate and download rent invoices from the Payments page."
            if "whatsapp" in q or "contact" in q or "landlord" in q:
                return "Use Chat for in-app messages or the WhatsApp button on your dashboard to contact your landlord directly."
            return f"Hi {user.fullname.split()[0]}, I can help with rent balance, due dates, maintenance, invoices, and contacting your landlord."

        if any(word in q for word in ["occupancy", "vacant", "occupied"]):
            return f"Occupancy: {stats.get('occupied_units', 0)} of {stats.get('total_units', 0)} units occupied ({stats.get('occupancy_rate', 0)}%). Vacant units: {stats.get('vacant_units', 0)}."
        if any(word in q for word in ["revenue", "income", "money", "expected"]):
            return f"Expected monthly revenue is KSh {stats.get('expected_revenue', 0):,.2f}. Collected this month is KSh {stats.get('collected_this_month', 0):,.2f}."
        if any(word in q for word in ["outstanding", "overdue", "arrears", "balance", "late"]):
            return f"Estimated outstanding rent this month including penalties is KSh {stats.get('outstanding', 0):,.2f}."
        if any(word in q for word in ["repair", "maintenance"]):
            return f"Pending maintenance requests: {stats.get('pending_repairs', 0)}. Open Repairs to approve or update status."
        if "tenant" in q:
            return f"You currently manage {stats.get('tenant_count', 0)} approved tenants."
        return f"Hi {user.fullname.split()[0]}, ask me about occupancy, revenue, outstanding rent, tenants, or repairs."
