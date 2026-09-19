from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from models import db
from models.user import User

bp = Blueprint('auth', __name__, url_prefix='/auth')
ADMIN_PHONE = '09055018315'

def normalize_phone(phone):
    raw = str(phone or '').strip()
    # Persian/Arabic digits -> Latin digits
    trans = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
    raw = raw.translate(trans)
    p = ''.join(ch for ch in raw if ch.isdigit())
    if p.startswith('98') and len(p) == 12:
        p = '0' + p[2:]
    elif p.startswith('0098') and len(p) == 14:
        p = '0' + p[4:]
    return p

@bp.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        identifier = request.form.get('identifier','').strip().lower()
        password = request.form.get('password','')
        normalized = normalize_phone(identifier)
        user = User.query.filter((User.email == identifier) | (User.phone == normalized)).first()
        if not user or not user.check_password(password):
            flash('ایمیل/شماره موبایل یا رمز عبور صحیح نیست.','danger')
            return render_template('login.html', mode='login')
        # The reserved admin number is always an administrator.
        if normalize_phone(user.phone) == ADMIN_PHONE and not user.is_admin:
            user.is_admin = True
            db.session.commit()
        login_user(user, remember=True)
        return redirect(request.args.get('next') or url_for('main.home'))
    return render_template('login.html', mode='login')

@bp.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        phone = normalize_phone(request.form.get('phone',''))
        password = request.form.get('password','')
        if len(name) < 2 or '@' not in email or len(phone) < 10 or len(password) < 6:
            flash('نام، ایمیل، شماره موبایل معتبر و رمز عبور حداقل ۶ کاراکتری وارد کنید.','danger')
            return render_template('login.html', mode='register')

        # Special admin number: an existing row is reused instead of trying
        # to INSERT another row and triggering UNIQUE users.phone.
        if phone == ADMIN_PHONE:
            user = User.query.filter_by(phone=ADMIN_PHONE).first()
            email_owner = User.query.filter_by(email=email).first()
            if user:
                if email_owner and email_owner.id != user.id:
                    flash('این ایمیل متعلق به حساب دیگری است؛ یک ایمیل دیگر وارد کنید.','warning')
                    return render_template('login.html', mode='register')
                user.name = name
                if email:
                    user.email = email
                user.is_admin = True
                user.set_password(password)
                db.session.commit()
                login_user(user, remember=True)
                flash('حساب شماره 09055018315 بازیابی و دسترسی مدیریت فعال شد.','success')
                return redirect(url_for('main.home'))

            if email_owner:
                flash('این ایمیل قبلاً ثبت شده است.','warning')
                return render_template('login.html', mode='register')

            user = User(name=name, email=email, phone=ADMIN_PHONE, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash('حساب مدیر ساخته شد و دسترسی مدیریت فعال است.','success')
            return redirect(url_for('main.home'))

        # Normal users retain normal uniqueness rules.
        if User.query.filter_by(email=email).first():
            flash('این ایمیل قبلاً ثبت شده است.','warning')
            return render_template('login.html', mode='register')
        if User.query.filter_by(phone=phone).first():
            flash('این شماره موبایل قبلاً ثبت شده است.','warning')
            return render_template('login.html', mode='register')

        user = User(name=name, email=email, phone=phone, is_admin=False)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        flash('حساب شما ساخته شد.','success')
        return redirect(url_for('main.home'))
    return render_template('login.html', mode='register')

@bp.get('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))
