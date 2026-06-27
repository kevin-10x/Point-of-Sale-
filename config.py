import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'database.db')}",
    )
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    WTF_CSRF_ENABLED = True

    # M-Pesa Daraja (Safaricom)
    MPESA_ENABLED = os.environ.get("MPESA_ENABLED", "false").lower() == "true"
    MPESA_ENVIRONMENT = os.environ.get("MPESA_ENVIRONMENT", "sandbox")
    MPESA_CONSUMER_KEY = os.environ.get("MPESA_CONSUMER_KEY", "")
    MPESA_CONSUMER_SECRET = os.environ.get("MPESA_CONSUMER_SECRET", "")
    MPESA_SHORTCODE = os.environ.get("MPESA_SHORTCODE", "")
    MPESA_PASSKEY = os.environ.get("MPESA_PASSKEY", "")
    MPESA_CALLBACK_URL = os.environ.get("MPESA_CALLBACK_URL", "")
    MPESA_TRANSACTION_TYPE = os.environ.get(
        "MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline"
    )

    SUBSCRIPTION_PLANS = {
        "starter": {"name": "Starter", "price": 500, "label": "KES 500/month"},
        "standard": {"name": "Standard", "price": 1500, "label": "KES 1,500/month"},
        "premium": {"name": "Premium", "price": 3000, "label": "KES 3,000/month"},
    }
    SUBSCRIPTION_PERIOD_DAYS = int(os.environ.get("SUBSCRIPTION_PERIOD_DAYS", "30"))

    # Public base URL for callbacks (set in production, e.g. https://your-app.railway.app)
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")
