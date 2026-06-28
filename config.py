import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 1. Fetch a non-pooling URL if available, fallback to POSTGRES_URL or DATABASE_URL
    _db_url = (
        os.environ.get("POSTGRES_URL_NON_POOLING") 
        or os.environ.get("POSTGRES_URL") 
        or os.environ.get("DATABASE_URL")
    )
    
    if _db_url:
        # Strip trailing connection pool options (like ?supa=...) that break psycopg2
        if "?" in _db_url:
            _db_url = _db_url.split("?")[0]
            
        # SQLAlchemy 1.4+ requires 'postgresql://' instead of 'postgres://'
        if _db_url.startswith("postgres://"):
            _db_url = _db_url.replace("postgres://", "postgresql://", 1)
            
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'database.db')}"

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
