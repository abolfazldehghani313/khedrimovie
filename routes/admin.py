from datetime import datetime
from pathlib import Path
import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from sqlalchemy import desc
from werkzeug.utils import secure_filename

from models import db
from models.content import Content, Episode, VideoVariant
from models.extra import Advertisement, Comment, DiscountCode, Genre, Payment, Setting
from models.subscription import Subscription, SubscriptionPlan
from models.user import User, WatchHistory
from services.auth import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

QUALITY_OPTIONS = ["240p", "360p", "480p", "720p", "1080p"]
POSTER_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "m4v", "mkv", "avi"}


def _slug(text):
    return re.sub(r"[^\w\u0600-\u06ff]+", "-", text.strip().lower(), flags=re.UNICODE).strip("-") or "content"


def admin_context(active):
    return {"active": active}


def _upload_file(field, folder, allowed):
    file = request.files.get(field)
    if not file or not file.filename:
        return "", 0
    original = secure_filename(file.filename)
    ext = Path(original).suffix.lower().lstrip(".")
    if ext not in allowed:
        raise ValueError(f"فرمت فایل «{ext or 'نامشخص'}» برای این بخش مجاز نیست.")
    target_dir = Path(current_app.static_folder) / "uploads" / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    filename = f"{stamp}_{original}"
    path = target_dir / filename
    file.save(path)
    return url_for("static", filename=f"uploads/{folder}/{filename}"), path.stat().st_size


def _delete_local_upload(url):
    if not url or not url.startswith("/static/uploads/"):
        return
    try:
        root = Path(current_app.static_folder).resolve()
        path = (root / url[len("/static/"):]).resolve()
        if root in path.parents and path.exists():
            path.unlink()
    except OSError:
        pass


def _genres():
    return Genre.query.order_by(Genre.name).all()


def _content_form(item, kind, active=None):
    return render_template(
        "admin/content_form.html",
        item=item,
        kind=kind,
        genres=_genres(),
        qualities=QUALITY_OPTIONS,
        **admin_context(active or ("movies" if kind == "movie" else "series")),
    )


@bp.get("/")
@admin_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "movies": Content.query.filter_by(kind="movie").count(),
        "series": Content.query.filter_by(kind="series").count(),
        "subscriptions": Subscription.query.count(),
        "payments": Payment.query.count(),
        "comments": Comment.query.count(),
        "ads": Advertisement.query.count(),
    }
    latest = Content.query.order_by(desc(Content.created_at)).limit(10).all()
    return render_template("admin/dashboard.html", stats=stats, latest=latest, **admin_context("dashboard"))


@bp.route("/movies", methods=["GET", "POST"])
@admin_required
def movies():
    if request.method == "POST":
        return _save_content("movie")
    return render_template(
        "admin/list.html",
        title="فیلم‌ها",
        items=Content.query.filter_by(kind="movie").order_by(desc(Content.created_at)).all(),
        type="movie",
        **admin_context("movies"),
    )


@bp.route("/series", methods=["GET", "POST"])
@admin_required
def series():
    if request.method == "POST":
        return _save_content("series")
    return render_template(
        "admin/list.html",
        title="سریال‌ها",
        items=Content.query.filter_by(kind="series").order_by(desc(Content.created_at)).all(),
        type="series",
        **admin_context("series"),
    )


def _save_content(kind, item=None):
    title = request.form.get("title", "").strip()
    slug = _slug(request.form.get("slug", "") or title)
    old_poster = item.poster_url if item else ""

    if not item:
        if Content.query.filter_by(slug=slug).first():
            slug = f"{slug}-{Content.query.count() + 1}"
        item = Content(kind=kind, slug=slug)
        db.session.add(item)
        db.session.flush()

    item.title = title
    item.slug = slug
    item.description = request.form.get("description", "").strip()
    item.genre = request.form.get("genre", "درام")
    item.backdrop_url = request.form.get("backdrop_url", "").strip()
    item.trailer_url = request.form.get("trailer_url", "").strip()
    item.year = request.form.get("year", type=int)
    item.duration_minutes = request.form.get("duration_minutes", type=int)
    item.rating = request.form.get("rating", type=float) or 0
    item.is_premium = bool(request.form.get("is_premium"))
    item.is_published = bool(request.form.get("is_published"))

    try:
        if request.form.get("remove_poster"):
            item.poster_url = ""

        poster, _ = _upload_file("poster_file", "posters", POSTER_EXTENSIONS)
        if poster:
            item.poster_url = poster

        # هر کیفیت فایل مستقل دارد؛ فایل قبلی همان کیفیت با فایل جدید جایگزین می‌شود.
        for quality in QUALITY_OPTIONS:
            field = f"video_{quality.replace('p', '')}"
            remove_field = f"remove_video_{quality.replace('p', '')}"
            existing = VideoVariant.query.filter_by(content_id=item.id, episode_id=None, quality=quality).first()

            if request.form.get(remove_field) and existing:
                old_url = existing.file_url
                db.session.delete(existing)
                db.session.flush()
                _delete_local_upload(old_url)
                existing = None

            uploaded_url, file_size = _upload_file(field, "videos", VIDEO_EXTENSIONS)
            if uploaded_url:
                if existing:
                    _delete_local_upload(existing.file_url)
                    existing.file_url = uploaded_url
                    existing.file_size = file_size
                else:
                    db.session.add(VideoVariant(content_id=item.id, quality=quality, file_url=uploaded_url, file_size=file_size))

        db.session.flush()
        variants = VideoVariant.query.filter_by(content_id=item.id, episode_id=None).all()
        if variants:
            # برای سازگاری با پخش‌کننده قدیمی، بالاترین کیفیت موجود به عنوان فایل اصلی ثبت می‌شود.
            variants.sort(key=lambda v: int(v.quality.rstrip("p")), reverse=True)
            item.video_url = variants[0].file_url
        elif request.form.get("remove_all_videos"):
            item.video_url = ""

        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return _content_form(item, kind)
    except Exception:
        db.session.rollback()
        flash("ذخیره محتوا یا آپلود فایل انجام نشد. حجم و فرمت فایل را بررسی کنید.", "danger")
        return _content_form(item, kind)

    if item.poster_url != old_poster:
        _delete_local_upload(old_poster)
    flash("اطلاعات محتوا، پوستر و کیفیت‌های ویدئو با موفقیت ذخیره شد.", "success")
    return redirect(url_for("admin.movies" if kind == "movie" else "admin.series"))


@bp.route("/content/new/<kind>", methods=["GET", "POST"])
@admin_required
def new_content(kind):
    if kind not in ("movie", "series"):
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        return _save_content(kind)
    return _content_form(None, kind)


@bp.route("/content/<int:content_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_content(content_id):
    item = Content.query.get_or_404(content_id)
    if request.method == "POST":
        return _save_content(item.kind, item)
    return _content_form(item, item.kind)


@bp.post("/content/<int:content_id>/delete")
@admin_required
def delete_content(content_id):
    item = Content.query.get_or_404(content_id)
    urls = [item.poster_url, item.video_url] + [v.file_url for v in item.video_variants]
    for ep in item.episodes:
        urls += [v.file_url for v in ep.video_variants]
        urls.append(ep.video_url)
    db.session.delete(item)
    db.session.commit()
    for media_url in urls:
        _delete_local_upload(media_url)
    flash("محتوا، قسمت‌ها و فایل‌های مربوط به آن حذف شد.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


@bp.get("/episode/new")
@admin_required
def new_episode():
    series_items = Content.query.filter_by(kind="series").order_by(Content.title).all()
    return render_template("admin/episode_form.html", series=series_items, qualities=QUALITY_OPTIONS, **admin_context("series"))


@bp.route("/episodes", methods=["GET", "POST"])
@admin_required
def episodes():
    series_items = Content.query.filter_by(kind="series").order_by(Content.title).all()
    if request.method == "POST":
        try:
            episode = Episode(
                series_id=request.form.get("series_id", type=int),
                season_number=request.form.get("season_number", type=int) or 1,
                episode_number=request.form.get("episode_number", type=int) or 1,
                title=request.form.get("title", "قسمت جدید").strip(),
                description=request.form.get("description", "").strip(),
                duration_minutes=request.form.get("duration_minutes", type=int),
                is_premium=bool(request.form.get("is_premium")),
            )
            db.session.add(episode)
            db.session.flush()
            uploaded_any = False
            for quality in QUALITY_OPTIONS:
                field = f"video_{quality.replace('p', '')}"
                uploaded_url, file_size = _upload_file(field, "videos", VIDEO_EXTENSIONS)
                if uploaded_url:
                    db.session.add(VideoVariant(content_id=episode.series_id, episode_id=episode.id,
                                                quality=quality, file_url=uploaded_url, file_size=file_size))
                    uploaded_any = True
            if not uploaded_any:
                raise ValueError("حداقل یک فایل ویدئو برای یکی از کیفیت‌ها انتخاب کنید.")
            variants = VideoVariant.query.filter_by(episode_id=episode.id).all()
            variants.sort(key=lambda v: int(v.quality.rstrip("p")), reverse=True)
            episode.video_url = variants[0].file_url
            db.session.commit()
            flash("قسمت و کیفیت‌های ویدئوی آن با موفقیت اضافه شد.", "success")
            return redirect(url_for("admin.episodes"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return render_template("admin/episode_form.html", series=series_items, qualities=QUALITY_OPTIONS, **admin_context("series"))
        except Exception:
            db.session.rollback()
            flash("ذخیره قسمت یا آپلود ویدئو انجام نشد.", "danger")
            return render_template("admin/episode_form.html", series=series_items, qualities=QUALITY_OPTIONS, **admin_context("series"))
    eps = Episode.query.order_by(Episode.series_id, Episode.season_number, Episode.episode_number).all()
    return render_template("admin/episodes.html", series=series_items, episodes=eps, **admin_context("series"))


@bp.route("/genres", methods=["GET", "POST"])
@admin_required
def genres():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name and not Genre.query.filter_by(name=name).first():
            db.session.add(Genre(name=name))
            db.session.commit()
            flash("ژانر با موفقیت اضافه شد.", "success")
    return render_template("admin/simple.html", title="ژانرها", items=Genre.query.order_by(Genre.name).all(), form="genre", **admin_context("genres"))


@bp.get("/users")
@admin_required
def users():
    return render_template("admin/users.html", items=User.query.order_by(desc(User.created_at)).all(), **admin_context("users"))


@bp.get("/subscriptions")
@admin_required
def subscriptions():
    return render_template("admin/subscriptions.html", items=Subscription.query.order_by(desc(Subscription.starts_at)).all(), plans=SubscriptionPlan.query.all(), **admin_context("subscriptions"))


@bp.get("/payments")
@admin_required
def payments():
    rows = [[p.user.name if p.user else "-", f"{p.amount:,}", p.gateway, p.status, p.created_at.strftime("%Y/%m/%d")] for p in Payment.query.order_by(desc(Payment.created_at)).all()]
    return render_template("admin/simple_table.html", title="پرداخت‌ها", headers=["کاربر", "مبلغ", "درگاه", "وضعیت", "تاریخ"], rows=rows, **admin_context("payments"))


@bp.route("/ads", methods=["GET", "POST"])
@admin_required
def ads():
    if request.method == "POST":
        db.session.add(Advertisement(title=request.form.get("title", "تبلیغ"), media_url=request.form.get("media_url", ""),
                                     target_url=request.form.get("target_url", ""), placement=request.form.get("placement", "صفحه اصلی"),
                                     is_active=bool(request.form.get("is_active"))))
        db.session.commit()
        flash("تبلیغ با موفقیت اضافه شد.", "success")
    return render_template("admin/ads.html", items=Advertisement.query.order_by(desc(Advertisement.created_at)).all(), **admin_context("ads"))


@bp.get("/watch-report")
@admin_required
def watch_report():
    rows = [[h.user.name, h.content.title, f"{h.progress_seconds} ثانیه", h.updated_at.strftime("%Y/%m/%d %H:%M")] for h in WatchHistory.query.order_by(desc(WatchHistory.updated_at)).limit(200).all()]
    return render_template("admin/simple_table.html", title="گزارش تماشا", headers=["کاربر", "محتوا", "پیشرفت", "آخرین فعالیت"], rows=rows, **admin_context("watch"))


@bp.get("/comments")
@admin_required
def comments():
    return render_template("admin/comments.html", items=Comment.query.order_by(desc(Comment.created_at)).all(), **admin_context("comments"))


@bp.route("/discounts", methods=["GET", "POST"])
@admin_required
def discounts():
    if request.method == "POST":
        db.session.add(DiscountCode(code=request.form.get("code", "").strip().upper(), percent=request.form.get("percent", type=int) or 0,
                                    max_uses=request.form.get("max_uses", type=int) or 0))
        db.session.commit()
        flash("کد تخفیف با موفقیت ساخته شد.", "success")
    return render_template("admin/simple.html", title="کدهای تخفیف", items=DiscountCode.query.order_by(DiscountCode.id.desc()).all(), form="discount", **admin_context("discounts"))


@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        for key, value in request.form.items():
            if key.startswith("setting_"):
                setting_key = key[8:]
                setting = Setting.query.filter_by(key=setting_key).first() or Setting(key=setting_key)
                setting.value = value.strip()
                db.session.add(setting)
        db.session.commit()
        flash("تنظیمات پلتفرم با موفقیت ذخیره شد.", "success")
    values = {s.key: s.value for s in Setting.query.all()}
    return render_template("admin/settings.html", values=values, **admin_context("settings"))


@bp.route("/plans", methods=["GET", "POST"])
@admin_required
def plans():
    if request.method == "POST":
        db.session.add(SubscriptionPlan(name=request.form.get("name", "اشتراک"), price=request.form.get("price", type=int) or 0,
                                        duration_days=request.form.get("duration_days", type=int) or 30,
                                        description=request.form.get("description", "")))
        db.session.commit()
        flash("پلن اشتراک با موفقیت اضافه شد.", "success")
    return render_template("admin/plans.html", plans=SubscriptionPlan.query.order_by(SubscriptionPlan.duration_days).all(), **admin_context("subscriptions"))
