from datetime import datetime, timedelta
from . import db

class SubscriptionPlan(db.Model):
    __tablename__ = "subscription_plans"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Integer, nullable=False, default=0)
    duration_days = db.Column(db.Integer, nullable=False, default=30)
    description = db.Column(db.Text, default="", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

class Subscription(db.Model):
    __tablename__ = "subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("subscription_plans.id"), nullable=False)
    starts_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    user = db.relationship("User", back_populates="subscriptions")
    plan = db.relationship("SubscriptionPlan")

    @classmethod
    def create_for(cls, user, plan):
        now = datetime.utcnow()
        return cls(user=user, plan=plan, starts_at=now, ends_at=now + timedelta(days=plan.duration_days), is_active=True)
