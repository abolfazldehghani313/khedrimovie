from datetime import datetime
from . import db

class Genre(db.Model):
    __tablename__ = 'genres'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    amount = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(30), default='pending', nullable=False)
    gateway = db.Column(db.String(80), default='demo', nullable=False)
    reference = db.Column(db.String(180), default='', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship('User')

class Advertisement(db.Model):
    __tablename__ = 'advertisements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    media_url = db.Column(db.Text, default='', nullable=False)
    target_url = db.Column(db.Text, default='', nullable=False)
    placement = db.Column(db.String(80), default='home', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('contents.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user = db.relationship('User')
    content = db.relationship('Content')

class DiscountCode(db.Model):
    __tablename__ = 'discount_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False)
    percent = db.Column(db.Integer, default=0, nullable=False)
    max_uses = db.Column(db.Integer, default=0, nullable=False)
    used_count = db.Column(db.Integer, default=0, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False)
    value = db.Column(db.Text, default='', nullable=False)
