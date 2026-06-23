import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, "/tmp")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "repairs")
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "landlordpro-dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:////tmp/landlordpro.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = UPLOAD_FOLDER
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

    # Financial automation
    RENT_DUE_DAY = int(os.getenv("RENT_DUE_DAY", "5"))
    LATE_FEE_PERCENT = float(os.getenv("LATE_FEE_PERCENT", "5"))

    # JWT API
    JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

    # M-Pesa Daraja. If credentials are absent, the app safely uses simulation mode.
    MPESA_ENV = os.getenv("MPESA_ENV", "sandbox")
    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "http://127.0.0.1:5000/mpesa/callback")
    MPESA_PAYBILL = os.getenv("MPESA_PAYBILL", MPESA_SHORTCODE)
    MPESA_TILL = os.getenv("MPESA_TILL", "987654")

    # OpenAI assistant. If absent, rule-based assistant is used.
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Email/SMS notifications
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "25"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@landlordpro.local")
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "console")
    SMS_API_KEY = os.getenv("SMS_API_KEY")
    SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "LANDLORDPRO")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = ProductionConfig() if os.getenv("FLASK_ENV") == "production" else DevelopmentConfig()
