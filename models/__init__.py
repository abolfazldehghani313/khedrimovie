from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .user import User, WatchHistory, Favorite
from .content import Content, Episode, VideoVariant
from .subscription import SubscriptionPlan, Subscription
from .extra import Genre, Payment, Advertisement, Comment, DiscountCode, Setting

__all__ = ['db','User','WatchHistory','Favorite','Content','Episode','VideoVariant','SubscriptionPlan','Subscription',
           'Genre','Payment','Advertisement','Comment','DiscountCode','Setting']
