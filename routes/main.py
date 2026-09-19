from datetime import datetime
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file, current_app
from flask_login import current_user, login_required
from sqlalchemy import or_, desc
from models import db
from models.content import Content, Episode, VideoVariant
from models.user import Favorite, WatchHistory
from models.subscription import SubscriptionPlan, Subscription

main_bp = Blueprint("main", __name__)

def _published_query(kind=None):
    q = Content.query.filter_by(is_published=True)
    if kind:
        q = q.filter_by(kind=kind)
    return q

@main_bp.get("/")
def home():
    q = request.args.get("q", "").strip()
    genre = request.args.get("genre", "").strip()
    movies = _published_query("movie")
    series = _published_query("series")
    if q:
        cond = or_(Content.title.ilike(f"%{q}%"), Content.description.ilike(f"%{q}%"), Content.genre.ilike(f"%{q}%"))
        movies = movies.filter(cond)
        series = series.filter(cond)
    if genre:
        movies = movies.filter(Content.genre == genre)
        series = series.filter(Content.genre == genre)
    genres = [r[0] for r in db.session.query(Content.genre).filter(Content.is_published.is_(True)).distinct().order_by(Content.genre).all()]
    movies = movies.order_by(desc(Content.created_at))
    series = series.order_by(desc(Content.created_at))
    return render_template("home.html", featured=movies.limit(6).all(), movies=movies.limit(8).all(), series=series.limit(8).all(), genres=genres, q=q, genre=genre)

@main_bp.get("/movies")
def movies():
    items = _published_query("movie").order_by(desc(Content.created_at)).all()
    return render_template("movie.html", items=items, title="فیلم‌ها")

@main_bp.get("/series")
def series():
    items = _published_query("series").order_by(desc(Content.created_at)).all()
    return render_template("series.html", items=items, title="سریال‌ها")

@main_bp.get("/title/<slug>")
def title_detail(slug):
    item = Content.query.filter_by(slug=slug, is_published=True).first_or_404()
    favorite = False
    if current_user.is_authenticated:
        favorite = Favorite.query.filter_by(user_id=current_user.id, content_id=item.id).first() is not None
    return render_template("detail.html", item=item, favorite=favorite)

@main_bp.get("/watch/<slug>")
def watch(slug):
    item = Content.query.filter_by(slug=slug, is_published=True).first_or_404()
    if item.is_premium and not (current_user.is_authenticated and current_user.premium):
        flash("برای تماشای این محتوا، ابتدا یکی از اشتراک‌ها را فعال کنید.", "warning")
        return redirect(url_for("main.subscriptions", next=url_for("main.watch", slug=slug)))
    video_url = item.video_url
    episode = None
    eid = request.args.get("episode", type=int)
    if eid:
        episode = Episode.query.filter_by(id=eid, series_id=item.id).first_or_404()
        if episode.is_premium and not (current_user.is_authenticated and current_user.premium):
            flash("این قسمت ویژه است و نیاز به اشتراک دارد.", "warning")
            return redirect(url_for("main.subscriptions"))
        variants = sorted(episode.video_variants, key=lambda v: int(v.quality.rstrip("p")), reverse=True)
        video_url = variants[0].file_url if variants else episode.video_url
    else:
        variants = sorted([v for v in item.video_variants if v.episode_id is None], key=lambda v: int(v.quality.rstrip("p")), reverse=True)
        video_url = variants[0].file_url if variants else item.video_url
    if current_user.is_authenticated:
        history = WatchHistory.query.filter_by(user_id=current_user.id, content_id=item.id).first()
        if not history:
            history = WatchHistory(user_id=current_user.id, content_id=item.id, progress_seconds=0)
            db.session.add(history)
            db.session.commit()
    episodes = sorted(item.episodes, key=lambda e: (e.season_number, e.episode_number))
    return render_template("watch.html", item=item, episode=episode, episodes=episodes, video_url=video_url, variants=variants)

@main_bp.post("/favorite/<int:content_id>")
@login_required
def favorite(content_id):
    item = Content.query.get_or_404(content_id)
    fav = Favorite.query.filter_by(user_id=current_user.id, content_id=item.id).first()
    if fav:
        db.session.delete(fav)
        flash("از علاقه‌مندی‌ها حذف شد.", "info")
    else:
        db.session.add(Favorite(user_id=current_user.id, content_id=item.id))
        flash("به علاقه‌مندی‌ها اضافه شد.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("main.title_detail", slug=item.slug))

@main_bp.get("/download/<int:variant_id>")
def download_variant(variant_id):
    variant = VideoVariant.query.get_or_404(variant_id)
    item = Content.query.get_or_404(variant.content_id)
    if not item.is_published:
        abort(404)
    if item.is_premium and not (current_user.is_authenticated and current_user.premium):
        flash("برای دانلود این محتوای ویژه، ابتدا اشتراک خود را فعال کنید.", "warning")
        return redirect(url_for("main.subscriptions"))
    if variant.episode_id:
        episode = Episode.query.get_or_404(variant.episode_id)
        if episode.is_premium and not (current_user.is_authenticated and current_user.premium):
            flash("برای دانلود این قسمت ویژه، ابتدا اشتراک خود را فعال کنید.", "warning")
            return redirect(url_for("main.subscriptions"))
    if not variant.file_url.startswith("/static/uploads/"):
        return redirect(variant.file_url)
    root = Path(current_app.static_folder).resolve()
    path = (root / variant.file_url[len("/static/"):]).resolve()
    if root not in path.parents or not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=f"{item.slug}-{variant.quality}{path.suffix or '.mp4'}")


@main_bp.get("/subscriptions")
def subscriptions():
    plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.duration_days).all()
    return render_template("subscriptions.html", plans=plans)

@main_bp.post("/subscribe/<int:plan_id>")
@login_required
def subscribe(plan_id):
    plan = SubscriptionPlan.query.filter_by(id=plan_id, is_active=True).first_or_404()
    # V1: demo activation instead of real payment gateway.
    current = current_user.active_subscription
    if current:
        current.is_active = False
    subscription = Subscription.create_for(current_user, plan)
    db.session.add(subscription)
    db.session.commit()
    flash("اشتراک در حالت آزمایشی با موفقیت فعال شد. برای پرداخت واقعی، درگاه به V2 اضافه می‌شود.", "success")
    return redirect(url_for("main.profile"))

@main_bp.get("/profile")
@login_required
def profile():
    favs = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    history = WatchHistory.query.filter_by(user_id=current_user.id).order_by(WatchHistory.updated_at.desc()).limit(10).all()
    return render_template("profile.html", favs=favs, history=history)
