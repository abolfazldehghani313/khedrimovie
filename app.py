import os
from flask import Flask, render_template
from flask_login import LoginManager
from sqlalchemy import inspect, text
from config import Config
from models import db
from models.user import User
from models.extra import Setting
from routes import register_blueprints
from services.seed import seed_database

login_manager=LoginManager(); login_manager.login_view='auth.login'; login_manager.login_message='برای این بخش ابتدا وارد حساب شوید.'; login_manager.login_message_category='warning'

def migrate_database():
    inspector=inspect(db.engine)
    tables=inspector.get_table_names()
    if 'users' in tables:
        cols={c['name'] for c in inspector.get_columns('users')}
        if 'phone' not in cols:
            db.session.execute(text('ALTER TABLE users ADD COLUMN phone VARCHAR(30)'))
            db.session.commit()
            try: db.session.execute(text('CREATE UNIQUE INDEX ix_users_phone ON users (phone)')); db.session.commit()
            except Exception: db.session.rollback()

def create_app():
    app=Flask(__name__); app.config.from_object(Config); db.init_app(app); login_manager.init_app(app); register_blueprints(app)
    @login_manager.user_loader
    def load_user(user_id): return db.session.get(User,int(user_id))
    @app.context_processor
    def inject_globals():
        defaults = {
            'site_name': app.config['SITE_NAME'],
            'site_description': 'پلتفرم نمایش خانگی برای تماشای آنلاین فیلم و سریال',
        }
        try:
            settings = {s.key: s.value for s in Setting.query.all()}
            defaults.update({k: v for k, v in settings.items() if v is not None})
        except Exception:
            pass
        return {
            'site_name': defaults['site_name'] or app.config['SITE_NAME'],
            'site_description': defaults['site_description'],
            'hero_title': defaults.get('hero_title', 'فیلم و سریال موردعلاقه‌ات را همین حالا پیدا کن.'),
            'hero_description': defaults.get('hero_description', defaults['site_description']),
            'primary_color': defaults.get('primary_color', '#7c5cff'),
        }
    @app.errorhandler(403)
    def forbidden(_): return render_template('error.html',code=403,message='دسترسی به این بخش مجاز نیست.'),403
    @app.errorhandler(404)
    def not_found(_): return render_template('error.html',code=404,message='صفحه موردنظر پیدا نشد.'),404
    with app.app_context():
        db.create_all(); migrate_database(); seed_database()
    return app
app=create_app()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=os.getenv('FLASK_DEBUG','0')=='1')
