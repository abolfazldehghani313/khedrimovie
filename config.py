import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-please")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{INSTANCE_DIR / 'app.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Direct media uploads from the admin panel.
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SITE_NAME = os.getenv("SITE_NAME", "Niyaz VOD")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@niyaz-vod.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin123!")
