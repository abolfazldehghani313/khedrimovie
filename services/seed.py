from models import db
from models.user import User
from models.content import Content, Episode, VideoVariant
from models.extra import Genre, Setting
from models.subscription import SubscriptionPlan
from config import Config

ADMIN_PHONE = "09055018315"

DEFAULT_GENRES = [
    "اکشن", "ماجراجویی", "انیمیشن", "بیوگرافی", "تاریخی", "جنایی", "درام",
    "خانوادگی", "ترسناک", "رمانتیک", "عاشقانه", "علمی‌تخیلی", "فانتزی",
    "کمدی", "معمایی", "هیجان‌انگیز", "جنگی", "ورزشی", "مستند", "موزیکال",
    "کودک و نوجوان", "کوتاه", "وسترن", "نوآر", "رازآلود", "اجتماعی", "ایرانی", "مذهبی",
]

def normalize_phone(phone):
    digits = ''.join(ch for ch in (phone or '') if ch.isdigit())
    if digits.startswith('98') and len(digits) == 12:
        digits = '0' + digits[2:]
    return digits

def seed_database():
    existing_genres = {g.name for g in Genre.query.all()}
    for genre_name in DEFAULT_GENRES:
        if genre_name not in existing_genres:
            db.session.add(Genre(name=genre_name))

    default_settings = {
        'site_name': 'نیاز ویدئو',
        'description': 'پلتفرم نمایش خانگی برای تماشای آنلاین فیلم و سریال',
        'hero_title': 'فیلم و سریال موردعلاقه‌ات را همین حالا پیدا کن.',
        'hero_description': 'مجموعه‌ای از فیلم‌ها و سریال‌ها را با کیفیت دلخواه تماشا و دانلود کنید.',
        'primary_color': '#7c5cff',
        'contact_phone': '',
        'contact_email': '',
    }
    existing_settings = {s.key for s in Setting.query.all()}
    for key, value in default_settings.items():
        if key not in existing_settings:
            db.session.add(Setting(key=key, value=value))
    site_setting = Setting.query.filter_by(key='site_name').first()
    if site_setting and site_setting.value.strip().lower() in {'niyaz vod', 'niyazvod', 'vod'}:
        site_setting.value = 'نیاز ویدئو'

    # Never assign the unique admin phone to a second row. If an old database
    # already has the phone, promote that existing account instead.
    admin = User.query.filter_by(email=Config.ADMIN_EMAIL.lower()).first()
    phone_owner = User.query.filter_by(phone=ADMIN_PHONE).first()

    if phone_owner:
        phone_owner.is_admin = True
        if not phone_owner.password_hash:
            phone_owner.set_password(Config.ADMIN_PASSWORD)
        admin = phone_owner
    elif admin:
        admin.phone = ADMIN_PHONE
        admin.is_admin = True
    else:
        admin = User(
            name="مدیر سیستم",
            email=Config.ADMIN_EMAIL.lower(),
            phone=ADMIN_PHONE,
            is_admin=True,
        )
        admin.set_password(Config.ADMIN_PASSWORD)
        db.session.add(admin)

    if SubscriptionPlan.query.count() == 0:
        db.session.add_all([
            SubscriptionPlan(name="ماهانه", price=99000, duration_days=30, description="تماشای محتوای پریمیوم برای ۳۰ روز"),
            SubscriptionPlan(name="سه‌ماهه", price=249000, duration_days=90, description="پیشنهاد مناسب برای تماشای طولانی‌تر"),
            SubscriptionPlan(name="سالانه", price=799000, duration_days=365, description="یک سال دسترسی پریمیوم"),
        ])

    if Content.query.count() == 0:
        flower = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"
        contents = [
            Content(title="آخرین ایستگاه", slug="last-station", kind="movie", genre="درام", year=2026, duration_minutes=112, rating=8.7, is_premium=False,
                    description="یک درام معمایی درباره انتخاب‌هایی که مسیر زندگی را تغییر می‌دهند.",
                    poster_url="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=900&q=80",
                    backdrop_url="https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=1800&q=80", video_url=flower),
            Content(title="شهر بی‌خواب", slug="sleepless-city", kind="movie", genre="اکشن", year=2025, duration_minutes=128, rating=8.2, is_premium=True,
                    description="مامور سابقی که یک شب فرصت دارد پرونده‌ای قدیمی را برای همیشه ببندد.",
                    poster_url="https://images.unsplash.com/photo-1513106580091-1d82408b8cd2?auto=format&fit=crop&w=900&q=80",
                    backdrop_url="https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?auto=format&fit=crop&w=1800&q=80", video_url=flower),
            Content(title="خانه شماره هفت", slug="house-seven", kind="series", genre="معمایی", year=2026, duration_minutes=None, rating=9.0, is_premium=True,
                    description="سه دوست پس از بازگشت به شهری قدیمی با رازهای خانواده‌هایشان روبه‌رو می‌شوند.",
                    poster_url="https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=900&q=80",
                    backdrop_url="https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1800&q=80", video_url=""),
            Content(title="مدار قرمز", slug="red-orbit", kind="series", genre="علمی‌تخیلی", year=2025, duration_minutes=None, rating=8.6, is_premium=False,
                    description="خدمه یک ایستگاه فضایی در فاصله‌ای دور، پیام عجیبی دریافت می‌کنند.",
                    poster_url="https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=900&q=80",
                    backdrop_url="https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1800&q=80", video_url=""),
        ]
        db.session.add_all(contents)
        db.session.flush()
        house = next(c for c in contents if c.slug == "house-seven")
        red = next(c for c in contents if c.slug == "red-orbit")
        for series, prefix in [(house, "خانه شماره هفت"), (red, "مدار قرمز")]:
            for ep in range(1, 4):
                db.session.add(Episode(series=series, season_number=1, episode_number=ep, title=f"{prefix} - قسمت {ep}",
                                        description="قسمت نمونه برای نسخه اول پروژه.", video_url=flower, duration_minutes=42, is_premium=series.is_premium))

    db.session.commit()
