"""
Railway.app production settings.
Railway automatically sets DATABASE_URL and PORT.
"""
from .base import *  # noqa
import dj_database_url
import os

DEBUG = False

# Railway sets this automatically
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-railway-dashboard")

ALLOWED_HOSTS = ["*"]  # Railway provides its own domain

# Database — Railway injects DATABASE_URL automatically
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL", "sqlite:///db.sqlite3"),
        conn_max_age=600,
    )
}

# Static files via WhiteNoise (no separate server needed)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Redis (optional on Railway — falls back gracefully)
REDIS_URL = os.environ.get("REDIS_URL", "")
if REDIS_URL:
    CELERY_BROKER_URL = REDIS_URL
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Stripe
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PLATFORM_COMMISSION_PERCENT = float(os.environ.get("PLATFORM_COMMISSION_PERCENT", "10.0"))

# Email (console in production until SMTP configured)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
