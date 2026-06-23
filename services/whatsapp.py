from urllib.parse import quote_plus

def whatsapp_url(phone, message="Hello, I am contacting you from LandlordPro."):
    clean = (phone or "").replace("+", "").replace(" ", "").replace("-", "")
    return f"https://wa.me/{clean}?text={quote_plus(message)}"
