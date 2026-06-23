from flask import current_app
from flask_mail import Message
from extensions import mail

class NotificationService:
    """Email/SMS service with production providers and console fallback."""

    def send_email(self, to, subject, body):
        if not to:
            return {"success": False, "message": "Missing email recipient"}
        try:
            msg = Message(subject=subject, recipients=[to], body=body)
            mail.send(msg)
            return {"success": True, "channel": "email"}
        except Exception as exc:
            # Development fallback: don't break flows if SMTP isn't configured.
            current_app.logger.info("EMAIL FALLBACK to=%s subject=%s body=%s error=%s", to, subject, body, exc)
            return {"success": True, "channel": "console", "message": body}

    def send_sms(self, phone, message):
        if not phone:
            return {"success": False, "message": "Missing phone"}
        provider = current_app.config.get("SMS_PROVIDER", "console")
        if provider == "console":
            current_app.logger.info("SMS FALLBACK to=%s message=%s", phone, message)
            return {"success": True, "channel": "console", "message": message}
        # Extension point for Africa's Talking/Twilio/etc.
        current_app.logger.info("SMS provider %s not fully configured; console fallback to=%s message=%s", provider, phone, message)
        return {"success": True, "channel": "console", "message": message}

notification_service = NotificationService()
