from datetime import datetime
from . import db


class Content(db.Model):
    __tablename__ = "contents"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(240), unique=True, nullable=False, index=True)
    kind = db.Column(db.String(20), nullable=False, default="movie")
    description = db.Column(db.Text, default="", nullable=False)
    poster_url = db.Column(db.Text, default="", nullable=False)
    backdrop_url = db.Column(db.Text, default="", nullable=False)
    video_url = db.Column(db.Text, default="", nullable=False)
    trailer_url = db.Column(db.Text, default="", nullable=False)
    year = db.Column(db.Integer, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    genre = db.Column(db.String(120), default="درام", nullable=False)
    rating = db.Column(db.Float, default=8.0, nullable=False)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    episodes = db.relationship("Episode", back_populates="series", cascade="all, delete-orphan", lazy=True)
    video_variants = db.relationship("VideoVariant", back_populates="content", cascade="all, delete-orphan", lazy=True)


class Episode(db.Model):
    __tablename__ = "episodes"
    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey("contents.id"), nullable=False)
    season_number = db.Column(db.Integer, default=1, nullable=False)
    episode_number = db.Column(db.Integer, default=1, nullable=False)
    title = db.Column(db.String(220), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    video_url = db.Column(db.Text, default="", nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=True)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    series = db.relationship("Content", back_populates="episodes")
    video_variants = db.relationship("VideoVariant", back_populates="episode", cascade="all, delete-orphan", lazy=True)


class VideoVariant(db.Model):
    """A downloadable/playable version of a title at a specific quality."""
    __tablename__ = "video_variants"
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey("contents.id", ondelete="CASCADE"), nullable=False)
    episode_id = db.Column(db.Integer, db.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=True)
    quality = db.Column(db.String(10), nullable=False)  # 240p, 360p, 480p, 720p, 1080p
    file_url = db.Column(db.Text, nullable=False)
    file_size = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    content = db.relationship("Content", back_populates="video_variants", foreign_keys=[content_id])
    episode = db.relationship("Episode", back_populates="video_variants", foreign_keys=[episode_id])
