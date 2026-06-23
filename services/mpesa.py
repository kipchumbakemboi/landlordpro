from datetime import datetime
import base64
import random
import requests
from flask import current_app

class MpesaService:
    """Safaricom Daraja M-Pesa STK Push with simulation fallback.

    If MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET and MPESA_PASSKEY are not
    configured, the service returns a successful simulated payment so local
    development remains smooth.
    """

    def __init__(self):
        cfg = current_app.config if current_app else {}
        self.env = cfg.get("MPESA_ENV", "sandbox")
        self.consumer_key = cfg.get("MPESA_CONSUMER_KEY")
        self.consumer_secret = cfg.get("MPESA_CONSUMER_SECRET")
        self.shortcode = cfg.get("MPESA_SHORTCODE", "174379")
        self.passkey = cfg.get("MPESA_PASSKEY")
        self.callback_url = cfg.get("MPESA_CALLBACK_URL")
        self.paybill = cfg.get("MPESA_PAYBILL", self.shortcode)
        self.till = cfg.get("MPESA_TILL", "987654")
        base = "https://sandbox.safaricom.co.ke" if self.env == "sandbox" else "https://api.safaricom.co.ke"
        self.oauth_url = f"{base}/oauth/v1/generate?grant_type=client_credentials"
        self.stk_url = f"{base}/mpesa/stkpush/v1/processrequest"

    @property
    def live_ready(self):
        return all([self.consumer_key, self.consumer_secret, self.passkey, self.shortcode, self.callback_url])

    def _simulate(self, phone, amount, account_ref):
        checkout_id = f"ws_CO_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000,9999)}"
        receipt = f"LP{datetime.now().strftime('%m%d')}{random.randint(100000,999999)}"
        return {
            "success": True,
            "simulated": True,
            "checkout_request_id": checkout_id,
            "merchant_request_id": f"MR{random.randint(100000,999999)}",
            "receipt": receipt,
            "message": f"STK Push simulated to {phone}. Payment of KSh {float(amount):,.2f} confirmed.",
            "account_ref": account_ref,
        }

    def access_token(self):
        raw = f"{self.consumer_key}:{self.consumer_secret}".encode()
        headers = {"Authorization": "Basic " + base64.b64encode(raw).decode()}
        res = requests.get(self.oauth_url, headers=headers, timeout=20)
        res.raise_for_status()
        return res.json()["access_token"]

    def _password(self, timestamp):
        raw = f"{self.shortcode}{self.passkey}{timestamp}".encode()
        return base64.b64encode(raw).decode()

    def initiate_stk_push(self, phone, amount, account_ref):
        if not self.live_ready:
            return self._simulate(phone, amount, account_ref)
        phone = (phone or "").replace("+", "").replace(" ", "")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(float(amount)),
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": str(account_ref),
            "TransactionDesc": "LandlordPro rent payment",
        }
        headers = {"Authorization": f"Bearer {self.access_token()}", "Content-Type": "application/json"}
        res = requests.post(self.stk_url, json=payload, headers=headers, timeout=30)
        data = res.json()
        ok = res.ok and str(data.get("ResponseCode")) == "0"
        return {
            "success": ok,
            "simulated": False,
            "checkout_request_id": data.get("CheckoutRequestID"),
            "merchant_request_id": data.get("MerchantRequestID"),
            "receipt": data.get("CheckoutRequestID"),
            "message": data.get("CustomerMessage") or data.get("errorMessage") or "M-Pesa request processed.",
            "raw": data,
        }

    def receipt_text(self, payment):
        return f"""LANDLORDPRO MPESA RECEIPT
Receipt: {payment.mpesa_receipt}
Tenant: {payment.tenant.full_name}
Unit: {payment.unit.unit_number}
Amount: KSh {float(payment.amount):,.2f}
Date: {payment.payment_date:%Y-%m-%d %H:%M}
Status: {payment.status.upper()}"""
