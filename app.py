"""
Social Contract - Accountability Challenge App
Refactored to use SQLAlchemy ORM and Cloudinary for image storage
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from functools import wraps
import os
import re
import random
import string
import logging
from datetime import datetime, timedelta, date, timezone as tz
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dotenv import load_dotenv
from markupsafe import Markup

from models import (
    db, User, Challenge, ChallengeMember, Checkin, CheckinReaction,
    Achievement, UserAchievement, Notification, ChallengeComment, Nudge,
    seed_achievements
)
from cloudinary_helper import (
    init_cloudinary, upload_profile_photo, upload_checkin_photo,
    delete_image, get_optimized_url
)

load_dotenv()

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger('accountability_arena')

app = Flask(__name__)

# SECRET_KEY must be set via environment variable in production
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1':
        _secret_key = 'dev-only-insecure-key-do-not-use-in-prod'
        logger.warning('SECRET_KEY not set - using insecure dev key. Set SECRET_KEY for production.')
    else:
        raise RuntimeError('SECRET_KEY environment variable is required. Set it before starting the app.')
app.secret_key = _secret_key

# --- Database Configuration ---
# Support DATABASE_URL (Postgres on Render/Heroku) or fall back to SQLite for local dev
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Render/Heroku use postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local SQLite fallback
    DATA_DIR = os.environ.get('DATA_DIR', os.path.dirname(os.path.abspath(__file__)))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(DATA_DIR, "accountability_arena.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Test connections before using them
}

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# Initialize Cloudinary
cloudinary_configured = init_cloudinary()
if not cloudinary_configured:
    logger.warning('Cloudinary not configured - photo uploads will be disabled')

# --- Google OAuth Setup ---
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
    },
)

# Exempt OAuth callback from CSRF (Google redirects don't carry tokens)
csrf.exempt('auth_google_callback')

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

# --- Security Headers ---
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://res.cloudinary.com; "
        "connect-src 'self'; "
        "worker-src 'self'; "
        "manifest-src 'self'; "
        "frame-ancestors 'self'"
    )

    # Cache static assets aggressively (CSS, JS, images, icons)
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=2592000'  # 30 days
    return response


# --- Image validation ---
IMAGE_SIGNATURES = {
    b'\x89PNG\r\n\x1a\n': 'png',
    b'\xff\xd8\xff': 'jpg',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'RIFF': 'webp',
}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_image_file(file_storage):
    """Read magic bytes to verify the file is actually an image."""
    header = file_storage.read(12)
    file_storage.seek(0)
    if not header:
        return False
    for signature, fmt in IMAGE_SIGNATURES.items():
        if header.startswith(signature):
            if fmt == 'webp':
                return header[8:12] == b'WEBP'
            return True
    return False


# --- Helper Functions ---

def generate_join_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def safe_initial(name):
    if name and len(name) > 0:
        return name[0].upper()
    return '?'


app.jinja_env.globals['safe_initial'] = safe_initial


def render_avatar(display_name, photo_url=None, css_class='user-avatar'):
    """Render an avatar: photo if available, otherwise initials."""
    if photo_url:
        # Use Cloudinary URL optimization if it's a Cloudinary URL
        optimized_url = get_optimized_url(photo_url, width=80, height=80, crop='fill')
        return Markup(f'<img src="{optimized_url}" alt="{safe_initial(display_name)}" class="{css_class} avatar-img">')
    initial = safe_initial(display_name)
    return Markup(f'<div class="{css_class}">{initial}</div>')


app.jinja_env.globals['render_avatar'] = render_avatar


def validate_timezone(tz_name):
    """Return a valid IANA timezone name or 'UTC' as fallback."""
    if not tz_name or not isinstance(tz_name, str):
        return 'UTC'
    try:
        ZoneInfo(tz_name)
        return tz_name
    except (ZoneInfoNotFoundError, KeyError):
        return 'UTC'


def get_user_today(tz_name=None):
    """Get today's date in the user's timezone. Falls back to session, then UTC."""
    if not tz_name:
        tz_name = session.get('timezone', 'UTC')
    tz_name = validate_timezone(tz_name)
    now_utc = datetime.now(tz.utc)
    user_now = now_utc.astimezone(ZoneInfo(tz_name))
    return user_now.date()


def get_user_now(tz_name=None):
    """Get the current datetime in the user's timezone."""
    if not tz_name:
        tz_name = session.get('timezone', 'UTC')
    tz_name = validate_timezone(tz_name)
    now_utc = datetime.now(tz.utc)
    return now_utc.astimezone(ZoneInfo(tz_name))


def time_ago(dt):
    """Convert datetime to human-readable relative time."""
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            try:
                dt = datetime.strptime(dt, '%Y-%m-%d')
            except (ValueError, TypeError):
                return str(dt)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.utc)

    now = datetime.now(tz.utc)
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        mins = int(seconds // 60)
        return f'{mins}m ago'
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f'{hours}h ago'
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f'{days}d ago'
    else:
        return dt.strftime('%b %d')


app.jinja_env.globals['time_ago'] = time_ago


def create_notification(user_id, notif_type, title, message, link=None):
    """Create a notification for a user."""
    notification = Notification(
        user_id=user_id,
        type=notif_type,
        title=title,
        message=message,
        link=link
    )
    db.session.add(notification)
    db.session.commit()


def check_achievements(user_id):
    """Check and award any earned achievements for a user."""
    user = User.query.get(user_id)
    if not user:
        return

    # Get achievements user hasn't earned yet
    earned_ids = [ua.achievement_id for ua in user.achievements]
    unearned = Achievement.query.filter(~Achievement.id.in_(earned_ids) if earned_ids else True).all()

    if not unearned:
        return

    # Calculate stats
    total_checkins = Checkin.query.filter_by(user_id=user_id).count()
    best_streak = db.session.query(db.func.max(ChallengeMember.best_streak)).filter_by(user_id=user_id).scalar() or 0
    total_points = db.session.query(db.func.sum(ChallengeMember.points)).filter_by(user_id=user_id).scalar() or 0
    challenges_joined = ChallengeMember.query.filter_by(user_id=user_id).count()
    challenges_created = Challenge.query.filter_by(creator_id=user_id).count()
    photo_checkins = Checkin.query.filter(Checkin.user_id == user_id, Checkin.photo_url.isnot(None)).count()

    stat_map = {
        'total_checkins': total_checkins,
        'streak': best_streak,
        'total_points': total_points,
        'challenges_joined': challenges_joined,
        'challenges_created': challenges_created,
        'photo_checkins': photo_checkins,
    }

    for achievement in unearned:
        if achievement.condition_type in stat_map:
            if stat_map[achievement.condition_type] >= achievement.condition_value:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id
                )
                db.session.add(user_achievement)
                create_notification(
                    user_id, 'achievement_earned',
                    'Achievement Unlocked',
                    f'You earned "{achievement.name}" - {achievement.description}',
                    url_for('achievements_page')
                )

    db.session.commit()


def check_completed_challenges(user_id):
    """Check and finalize any challenges that have ended."""
    today = get_user_today()

    # Get user's active challenges that have passed their end date
    memberships = ChallengeMember.query.filter_by(user_id=user_id).all()

    for membership in memberships:
        challenge = membership.challenge
        if challenge.end_date and challenge.end_date < today and not challenge.is_completed:
            # Find winner (highest points)
            winner_member = ChallengeMember.query.filter_by(
                challenge_id=challenge.id
            ).order_by(ChallengeMember.points.desc()).first()

            challenge.is_completed = True
            challenge.winner_id = winner_member.user_id if winner_member else None

            # Notify all members
            winner_name = winner_member.user.display_name if winner_member else 'No one'
            winner_points = winner_member.points if winner_member else 0

            for member in challenge.members:
                create_notification(
                    member.user_id, 'challenge_completed',
                    'Challenge Ended',
                    f'"{challenge.name}" has ended. {winner_name} won with {winner_points} points.',
                    url_for('view_challenge', challenge_id=challenge.id)
                )

    db.session.commit()


CHALLENGE_TEMPLATES = [
    {
        'id': 'exercise',
        'name': 'Exercise Daily',
        'description': 'Commit to at least 30 minutes of exercise every day.',
        'icon': '\U0001F3C3',
        'points_per_checkin': 10,
        'streak_bonus': 5,
        'verification_type': 'photo_optional',
        'suggested_duration': 30,
    },
    {
        'id': 'reading',
        'name': 'Read Every Day',
        'description': 'Read for at least 20 minutes daily. Books, articles, or long-form content.',
        'icon': '\U0001F4D6',
        'points_per_checkin': 10,
        'streak_bonus': 5,
        'verification_type': 'none',
        'suggested_duration': 30,
    },
    {
        'id': 'meditation',
        'name': 'Daily Meditation',
        'description': 'Practice mindfulness or meditation for at least 10 minutes each day.',
        'icon': '\U0001F9D8',
        'points_per_checkin': 10,
        'streak_bonus': 5,
        'verification_type': 'none',
        'suggested_duration': 21,
    },
    {
        'id': 'no_social_media',
        'name': 'No Social Media',
        'description': 'Stay off social media platforms for the duration of the challenge.',
        'icon': '\U0001F4F5',
        'points_per_checkin': 15,
        'streak_bonus': 8,
        'verification_type': 'none',
        'suggested_duration': 14,
    },
    {
        'id': 'hydration',
        'name': 'Drink 8 Glasses of Water',
        'description': 'Stay hydrated by drinking at least 8 glasses of water every day.',
        'icon': '\U0001F4A7',
        'points_per_checkin': 10,
        'streak_bonus': 3,
        'verification_type': 'none',
        'suggested_duration': 30,
    },
    {
        'id': 'journaling',
        'name': 'Daily Journaling',
        'description': 'Write in your journal every day. Reflect on your goals, wins, and learnings.',
        'icon': '\U0001F4DD',
        'points_per_checkin': 10,
        'streak_bonus': 5,
        'verification_type': 'none',
        'suggested_duration': 30,
    },
    {
        'id': 'early_riser',
        'name': 'Wake Up Before 7 AM',
        'description': 'Start your day early. Check in before 7 AM to prove you are up.',
        'icon': '\u2600\uFE0F',
        'points_per_checkin': 15,
        'streak_bonus': 10,
        'verification_type': 'photo_optional',
        'suggested_duration': 21,
    },
    {
        'id': 'coding',
        'name': 'Code Every Day',
        'description': 'Write code daily. Ship features, fix bugs, or learn something new.',
        'icon': '\U0001F4BB',
        'points_per_checkin': 10,
        'streak_bonus': 5,
        'verification_type': 'photo_optional',
        'suggested_duration': 30,
    },
]


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# --- Routes ---

@app.route('/sw.js')
def service_worker():
    """Serve service worker from root scope with dynamic cache version."""
    import hashlib
    static_files = ['style.css', 'script.js', 'challenge.js', 'create-challenge.js']
    mtimes = ''
    for f in static_files:
        fpath = os.path.join(app.static_folder, f)
        if os.path.exists(fpath):
            mtimes += str(os.path.getmtime(fpath))
    version = 'sc-' + hashlib.md5(mtimes.encode()).hexdigest()[:8]

    sw_path = os.path.join(app.static_folder, 'sw.js')
    with open(sw_path, 'r') as f:
        content = f.read()
    content = content.replace('__SW_VERSION__', version)

    response = app.make_response(content)
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Cache-Control'] = 'no-cache'
    return response


@app.route('/offline')
def offline():
    return render_template('offline.html')


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        display_name = request.form.get('display_name', '').strip()
        user_timezone = validate_timezone(request.form.get('timezone', ''))

        if not username or not password or not email:
            flash('Username, email, and password are required.', 'error')
            return redirect(url_for('register'))

        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'error')
            return redirect(url_for('register'))

        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
            return redirect(url_for('register'))

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            display_name=display_name or username,
            email=email,
            timezone=user_timezone
        )
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username
        session['display_name'] = user.display_name
        session['profile_photo'] = None
        session['timezone'] = user_timezone

        flash('Account created. Welcome to Social Contract.', 'success')
        return redirect(url_for('explore'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip().lower()
        password = request.form.get('password', '')

        # Allow login with either username or email
        if '@' in login_id:
            user = User.query.filter_by(email=login_id).first()
        else:
            user = User.query.filter_by(username=login_id).first()

        if user and user.password_hash and check_password_hash(user.password_hash, password):
            # Update timezone from client if provided
            login_tz = validate_timezone(request.form.get('timezone', ''))
            if login_tz != 'UTC' or not user.timezone:
                user.timezone = login_tz
                db.session.commit()

            session['user_id'] = user.id
            session['username'] = user.username
            session['display_name'] = user.display_name
            session['profile_photo'] = user.profile_photo
            session['timezone'] = login_tz if login_tz != 'UTC' else (user.timezone or 'UTC')

            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username/email or password.', 'error')

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


# --- Google OAuth Routes ---

@app.route('/auth/google')
def auth_google():
    """Redirect user to Google's OAuth 2.0 consent screen."""
    redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/auth/google/callback')
def auth_google_callback():
    """Handle the callback from Google after user grants consent."""
    try:
        token = google.authorize_access_token()
    except Exception:
        flash('Google authentication failed. Please try again.', 'error')
        return redirect(url_for('login'))

    user_info = token.get('userinfo')
    if not user_info:
        try:
            resp = google.get('https://openidconnect.googleapis.com/v1/userinfo')
            user_info = resp.json()
        except Exception:
            flash('Could not retrieve your Google account information.', 'error')
            return redirect(url_for('login'))

    google_id = user_info.get('sub')
    email = user_info.get('email', '')
    name = user_info.get('name', '')

    if not google_id:
        flash('Could not retrieve your Google account information.', 'error')
        return redirect(url_for('login'))

    # Case 1: Returning Google user
    user = User.query.filter_by(google_id=google_id).first()
    if user:
        session['user_id'] = user.id
        session['username'] = user.username
        session['display_name'] = user.display_name
        session['profile_photo'] = user.profile_photo
        session['timezone'] = user.timezone or 'UTC'
        flash('Logged in with Google.', 'success')
        return redirect(url_for('dashboard'))

    # Case 2: Account linking - email matches existing user
    if email:
        existing_user = User.query.filter(
            (User.email == email) | (User.username == email.split('@')[0].lower())
        ).first()
        if existing_user and not existing_user.google_id:
            existing_user.google_id = google_id
            existing_user.email = existing_user.email or email
            db.session.commit()

            session['user_id'] = existing_user.id
            session['username'] = existing_user.username
            session['display_name'] = existing_user.display_name
            session['profile_photo'] = existing_user.profile_photo
            session['timezone'] = existing_user.timezone or 'UTC'
            flash('Google account linked to your existing account.', 'success')
            return redirect(url_for('dashboard'))

    # Case 3: Brand new user
    base_username = email.split('@')[0].lower() if email else 'user'
    base_username = re.sub(r'[^a-z0-9_]', '', base_username)
    if len(base_username) < 3:
        base_username = 'user'

    username = base_username
    while User.query.filter_by(username=username).first():
        suffix = ''.join(random.choices(string.digits, k=4))
        username = f"{base_username}_{suffix}"

    user = User(
        username=username,
        display_name=name or username,
        google_id=google_id,
        email=email
    )
    db.session.add(user)
    db.session.commit()

    session['user_id'] = user.id
    session['username'] = user.username
    session['display_name'] = user.display_name
    session['profile_photo'] = None
    session['timezone'] = 'UTC'

    flash('Account created with Google. Welcome to Social Contract!', 'success')
    return redirect(url_for('explore'))


@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    today = get_user_today()

    check_completed_challenges(user_id)

    # Get active challenges
    memberships = ChallengeMember.query.filter_by(user_id=user_id).join(Challenge).filter(
        Challenge.is_completed == False
    ).all()

    challenges = []
    for m in memberships:
        c = m.challenge
        checked_in_today = Checkin.query.filter_by(
            challenge_id=c.id, user_id=user_id, checkin_date=today
        ).first() is not None

        challenges.append({
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'join_code': c.join_code,
            'verification_type': c.verification_type,
            'end_date': c.end_date,
            'points_per_checkin': c.points_per_checkin,
            'streak_bonus': c.streak_bonus,
            'creator_name': c.creator.display_name,
            'member_count': len(c.members),
            'points': m.points,
            'current_streak': m.current_streak,
            'best_streak': m.best_streak,
            'checked_in_today': checked_in_today,
        })

    # Get completed challenges
    completed_memberships = ChallengeMember.query.filter_by(user_id=user_id).join(Challenge).filter(
        Challenge.is_completed == True
    ).all()

    completed_challenges = []
    for m in completed_memberships:
        c = m.challenge
        completed_challenges.append({
            'id': c.id,
            'name': c.name,
            'end_date': c.end_date,
            'creator_name': c.creator.display_name,
            'winner_name': c.winner.display_name if c.winner else None,
            'member_count': len(c.members),
            'points': m.points,
            'current_streak': m.current_streak,
            'best_streak': m.best_streak,
        })

    # Calculate stats
    total_points = db.session.query(db.func.sum(ChallengeMember.points)).filter_by(user_id=user_id).scalar() or 0
    best_current_streak = db.session.query(db.func.max(ChallengeMember.current_streak)).filter_by(user_id=user_id).scalar() or 0
    all_time_best_streak = db.session.query(db.func.max(ChallengeMember.best_streak)).filter_by(user_id=user_id).scalar() or 0
    active_challenges = len(challenges)

    stats = {
        'total_points': total_points,
        'best_current_streak': best_current_streak,
        'all_time_best_streak': all_time_best_streak,
        'active_challenges': active_challenges,
    }

    # Recent activity
    recent_checkins = Checkin.query.filter_by(user_id=user_id).order_by(
        Checkin.created_at.desc()
    ).limit(5).all()

    recent_activity = [{
        'checkin_date': c.checkin_date,
        'created_at': c.created_at,
        'challenge_name': c.challenge.name,
        'note': c.note,
        'photo_url': c.photo_url,
    } for c in recent_checkins]

    today_done = sum(1 for c in challenges if c['checked_in_today'])
    today_total = len(challenges)

    return render_template('dashboard.html',
                         challenges=challenges,
                         completed_challenges=completed_challenges,
                         stats=stats,
                         recent_activity=recent_activity,
                         today=today.isoformat(),
                         today_done=today_done,
                         today_total=today_total)


@app.route('/challenge/create', methods=['GET', 'POST'])
@login_required
def create_challenge():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        is_public = request.form.get('is_public') == 'on'
        points_per_checkin = int(request.form.get('points_per_checkin', 10))
        streak_bonus = int(request.form.get('streak_bonus', 5))
        verification_type = request.form.get('verification_type', 'none')
        end_date_str = request.form.get('end_date', '').strip()
        milestone_target = request.form.get('milestone_target', '').strip()
        milestone_target = int(milestone_target) if milestone_target else None

        if not name:
            flash('Challenge name is required.', 'error')
            return redirect(url_for('create_challenge'))

        if verification_type not in ('none', 'photo_optional', 'photo_required'):
            verification_type = 'none'

        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                if end_date <= get_user_today():
                    flash('End date must be in the future.', 'error')
                    return redirect(url_for('create_challenge'))
            except ValueError:
                flash('Invalid date format.', 'error')
                return redirect(url_for('create_challenge'))

        # Generate unique join code
        join_code = generate_join_code()
        while Challenge.query.filter_by(join_code=join_code).first():
            join_code = generate_join_code()

        challenge = Challenge(
            name=name,
            description=description,
            creator_id=session['user_id'],
            join_code=join_code,
            is_public=is_public,
            points_per_checkin=points_per_checkin,
            streak_bonus=streak_bonus,
            verification_type=verification_type,
            end_date=end_date,
            milestone_target=milestone_target
        )
        db.session.add(challenge)
        db.session.flush()  # Get the challenge ID

        # Add creator as first member
        membership = ChallengeMember(
            challenge_id=challenge.id,
            user_id=session['user_id']
        )
        db.session.add(membership)
        db.session.commit()

        check_achievements(session['user_id'])

        flash(f'Challenge created. Share code: {join_code}', 'success')
        return redirect(url_for('view_challenge', challenge_id=challenge.id))

    return render_template('create_challenge.html', templates=CHALLENGE_TEMPLATES)


@app.route('/challenge/join', methods=['GET', 'POST'])
@login_required
def join_challenge():
    if request.method == 'POST':
        join_code = request.form.get('join_code', '').strip().upper()

        if not join_code:
            flash('Please enter a join code.', 'error')
            return redirect(url_for('join_challenge'))

        challenge = Challenge.query.filter_by(join_code=join_code).first()

        if not challenge:
            flash('Invalid join code.', 'error')
            return redirect(url_for('join_challenge'))

        if challenge.is_completed:
            flash('This challenge has already ended.', 'error')
            return redirect(url_for('join_challenge'))

        if ChallengeMember.query.filter_by(
            challenge_id=challenge.id, user_id=session['user_id']
        ).first():
            flash('You are already in this challenge.', 'error')
            return redirect(url_for('view_challenge', challenge_id=challenge.id))

        membership = ChallengeMember(
            challenge_id=challenge.id,
            user_id=session['user_id']
        )
        db.session.add(membership)
        db.session.commit()

        if challenge.creator_id != session['user_id']:
            create_notification(
                challenge.creator_id, 'challenge_activity',
                'New Member',
                f'{session["display_name"]} joined your challenge "{challenge.name}".',
                url_for('view_challenge', challenge_id=challenge.id)
            )

        check_achievements(session['user_id'])

        flash(f'Joined "{challenge.name}" successfully.', 'success')
        return redirect(url_for('view_challenge', challenge_id=challenge.id))

    # Auto-join from magic link: /challenge/join?code=XYZ123
    prefill_code = request.args.get('code', '').strip().upper()[:6]
    if prefill_code:
        challenge = Challenge.query.filter_by(join_code=prefill_code).first()
        if challenge:
            # Already a member — go straight to challenge
            if ChallengeMember.query.filter_by(
                challenge_id=challenge.id, user_id=session['user_id']
            ).first():
                return redirect(url_for('view_challenge', challenge_id=challenge.id))

            # Auto-join if challenge is still active
            if not challenge.is_completed:
                membership = ChallengeMember(
                    challenge_id=challenge.id,
                    user_id=session['user_id']
                )
                db.session.add(membership)
                db.session.commit()

                if challenge.creator_id != session['user_id']:
                    create_notification(
                        challenge.creator_id, 'challenge_activity',
                        'New Member',
                        f'{session["display_name"]} joined your challenge "{challenge.name}".',
                        url_for('view_challenge', challenge_id=challenge.id)
                    )

                check_achievements(session['user_id'])
                flash(f'Joined "{challenge.name}" successfully.', 'success')
                return redirect(url_for('view_challenge', challenge_id=challenge.id))

    return render_template('join_challenge.html', prefill_code=prefill_code)


@app.route('/challenge/<int:challenge_id>')
@login_required
def view_challenge(challenge_id):
    user_id = session['user_id']
    today = get_user_today()

    challenge = Challenge.query.get_or_404(challenge_id)

    membership = ChallengeMember.query.filter_by(
        challenge_id=challenge_id, user_id=user_id
    ).first()

    if not membership:
        # Redirect non-members to join page with code pre-filled
        flash(f'Join "{challenge.name}" to view this challenge.', 'info')
        return redirect(url_for('join_challenge', code=challenge.join_code))

    # Build leaderboard
    leaderboard = []
    for m in challenge.members:
        checked_in_today = Checkin.query.filter_by(
            challenge_id=challenge_id, user_id=m.user_id, checkin_date=today
        ).first() is not None

        leaderboard.append({
            'display_name': m.user.display_name,
            'username': m.user.username,
            'profile_photo': m.user.profile_photo,
            'points': m.points,
            'current_streak': m.current_streak,
            'best_streak': m.best_streak,
            'user_id': m.user_id,
            'checked_in_today': checked_in_today,
        })

    leaderboard.sort(key=lambda x: (-x['points'], -x['current_streak']))

    checked_in_today = Checkin.query.filter_by(
        challenge_id=challenge_id, user_id=user_id, checkin_date=today
    ).first() is not None

    # Recent checkins with reactions
    recent_checkins = Checkin.query.filter_by(
        challenge_id=challenge_id
    ).order_by(Checkin.created_at.desc()).limit(20).all()

    reactions_map = {}
    for c in recent_checkins:
        reactions = {}
        for r in c.reactions:
            if r.reaction not in reactions:
                reactions[r.reaction] = {'count': 0, 'user_reacted': False}
            reactions[r.reaction]['count'] += 1
            if r.user_id == user_id:
                reactions[r.reaction]['user_reacted'] = True
        reactions_map[c.id] = [
            {'reaction': k, 'count': v['count'], 'user_reacted': v['user_reacted']}
            for k, v in reactions.items()
        ]

    comments = ChallengeComment.query.filter_by(
        challenge_id=challenge_id
    ).order_by(ChallengeComment.created_at.desc()).limit(30).all()

    # Days remaining
    days_remaining = None
    if challenge.end_date and not challenge.is_completed:
        days_remaining = (challenge.end_date - today).days

    # Milestone progress
    milestone_progress = None
    if challenge.milestone_target:
        total_checkins = Checkin.query.filter_by(
            challenge_id=challenge_id, user_id=user_id
        ).count()
        milestone_progress = {
            'current': total_checkins,
            'target': challenge.milestone_target,
            'percent': min(100, round(total_checkins / challenge.milestone_target * 100)),
        }

    # Check-in preview
    yesterday = today - timedelta(days=1)
    checked_yesterday = Checkin.query.filter_by(
        challenge_id=challenge_id, user_id=user_id, checkin_date=yesterday
    ).first() is not None

    current_streak = membership.current_streak
    has_freeze = membership.streak_freezes > 0

    checkin_preview = {}
    if checked_yesterday:
        preview_streak = current_streak + 1
    elif current_streak > 0 and has_freeze:
        preview_streak = current_streak + 1
        checkin_preview['freeze_will_be_used'] = True
    else:
        preview_streak = 1

    preview_points = challenge.points_per_checkin
    if preview_streak > 1:
        preview_points += challenge.streak_bonus * (preview_streak - 1)

    next_freeze_at = ((current_streak // 7) + 1) * 7
    days_to_next_freeze = next_freeze_at - current_streak

    checkin_preview['points'] = preview_points
    checkin_preview['streak'] = preview_streak
    checkin_preview['next_freeze_at'] = next_freeze_at
    checkin_preview['days_to_next_freeze'] = days_to_next_freeze

    # Checkin time if already checked in
    checkin_time = None
    if checked_in_today:
        checkin_row = Checkin.query.filter_by(
            challenge_id=challenge_id, user_id=user_id, checkin_date=today
        ).first()
        if checkin_row:
            checkin_time = checkin_row.created_at

    return render_template('challenge.html',
                         challenge=challenge,
                         membership=membership,
                         leaderboard=leaderboard,
                         checked_in_today=checked_in_today,
                         recent_checkins=recent_checkins,
                         reactions_map=reactions_map,
                         comments=comments,
                         days_remaining=days_remaining,
                         milestone_progress=milestone_progress,
                         checkin_preview=checkin_preview,
                         checkin_time=checkin_time,
                         today=today.isoformat())


@app.route('/challenge/<int:challenge_id>/checkin', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def checkin(challenge_id):
    user_id = session['user_id']

    # Timezone handling
    client_tz = validate_timezone(request.form.get('client_timezone', ''))
    user_tz = client_tz if client_tz != 'UTC' else session.get('timezone', 'UTC')

    client_date = request.form.get('client_date', '').strip()
    user_today = get_user_today(user_tz)

    if client_date and re.match(r'^\d{4}-\d{2}-\d{2}$', client_date):
        try:
            parsed = datetime.strptime(client_date, '%Y-%m-%d').date()
            if abs((user_today - parsed).days) <= 1:
                today = parsed
            else:
                today = user_today
        except ValueError:
            today = user_today
    else:
        today = user_today

    yesterday = today - timedelta(days=1)
    note = request.form.get('note', '').strip()

    membership = ChallengeMember.query.filter_by(
        challenge_id=challenge_id, user_id=user_id
    ).first()

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not membership:
        if is_ajax:
            return jsonify({'error': 'You are not a member of this challenge.'}), 400
        flash('You are not a member of this challenge.', 'error')
        return redirect(url_for('dashboard'))

    challenge = Challenge.query.get(challenge_id)
    if challenge.is_completed:
        if is_ajax:
            return jsonify({'error': 'This challenge has already ended.'}), 400
        flash('This challenge has already ended.', 'error')
        return redirect(url_for('view_challenge', challenge_id=challenge_id))

    if Checkin.query.filter_by(
        challenge_id=challenge_id, user_id=user_id, checkin_date=today
    ).first():
        if is_ajax:
            return jsonify({'error': 'Already checked in today.'}), 400
        flash('Already checked in today.', 'error')
        return redirect(url_for('view_challenge', challenge_id=challenge_id))

    # Handle photo upload to Cloudinary
    photo_url = None
    verification_type = challenge.verification_type or 'none'

    if 'photo' in request.files:
        photo = request.files['photo']
        if photo and photo.filename and allowed_file(photo.filename):
            if not validate_image_file(photo):
                if is_ajax:
                    return jsonify({'error': 'Uploaded file is not a valid image.'}), 400
                flash('Uploaded file is not a valid image.', 'error')
                return redirect(url_for('view_challenge', challenge_id=challenge_id))

            if cloudinary_configured:
                photo_url = upload_checkin_photo(photo, challenge_id, user_id, today.isoformat())
                if not photo_url:
                    logger.warning(f'Failed to upload checkin photo for user {user_id}')

    if verification_type == 'photo_required' and not photo_url:
        if is_ajax:
            return jsonify({'error': 'Photo proof is required for this challenge.'}), 400
        flash('Photo proof is required for this challenge.', 'error')
        return redirect(url_for('view_challenge', challenge_id=challenge_id))

    # Streak calculation with freeze support
    checked_yesterday = Checkin.query.filter_by(
        challenge_id=challenge_id, user_id=user_id, checkin_date=yesterday
    ).first() is not None

    freeze_used = False
    if checked_yesterday:
        new_streak = membership.current_streak + 1
    else:
        if membership.current_streak > 0 and membership.streak_freezes > 0:
            new_streak = membership.current_streak + 1
            freeze_used = True
        else:
            new_streak = 1

    points_earned = challenge.points_per_checkin
    if new_streak > 1:
        points_earned += challenge.streak_bonus * (new_streak - 1)

    # Award freeze for 7-day milestones
    freeze_earned = 0
    old_streak = membership.current_streak
    if new_streak >= 7:
        old_milestones = old_streak // 7
        new_milestones = new_streak // 7
        freeze_earned = new_milestones - old_milestones

    # Create checkin
    checkin_obj = Checkin(
        challenge_id=challenge_id,
        user_id=user_id,
        checkin_date=today,
        note=note,
        photo_url=photo_url
    )
    db.session.add(checkin_obj)

    # Update membership
    membership.points += points_earned
    membership.current_streak = new_streak
    membership.best_streak = max(membership.best_streak, new_streak)
    membership.streak_freezes = max(0, membership.streak_freezes + freeze_earned - (1 if freeze_used else 0))
    if freeze_used:
        membership.freezes_used += 1

    # Update user total points
    user = User.query.get(user_id)
    user.total_points += points_earned

    db.session.commit()

    check_achievements(user_id)

    # Build response message
    msg_parts = [f'+{points_earned} points (Streak: {new_streak})']
    if freeze_used:
        msg_parts.append('Streak freeze used!')
    if freeze_earned > 0:
        msg_parts.append(f'+{freeze_earned} freeze{"s" if freeze_earned > 1 else ""} earned!')
    message = f'Check-in recorded. {" ".join(msg_parts)}'

    if is_ajax:
        return jsonify({
            'success': True,
            'message': message,
            'points_earned': points_earned,
            'new_streak': new_streak,
            'freeze_used': freeze_used,
            'freeze_earned': freeze_earned,
        })

    flash(message, 'success')
    return redirect(url_for('view_challenge', challenge_id=challenge_id))


@app.route('/challenge/<int:challenge_id>/react', methods=['POST'])
@limiter.limit("30 per minute")
@login_required
def react_to_checkin(challenge_id):
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}
    checkin_id = data.get('checkin_id')

    if checkin_id is not None:
        try:
            checkin_id = int(checkin_id)
        except (ValueError, TypeError):
            checkin_id = None

    reaction = data.get('reaction', '')
    allowed_reactions = ['&#128077;', '&#128293;', '&#128170;', '&#127881;']

    if not checkin_id or reaction not in allowed_reactions:
        return jsonify({'error': 'Invalid reaction'}), 400

    existing = CheckinReaction.query.filter_by(
        checkin_id=checkin_id, user_id=user_id, reaction=reaction
    ).first()

    if existing:
        db.session.delete(existing)
    else:
        new_reaction = CheckinReaction(
            checkin_id=checkin_id,
            user_id=user_id,
            reaction=reaction
        )
        db.session.add(new_reaction)

    db.session.commit()

    count = CheckinReaction.query.filter_by(
        checkin_id=checkin_id, reaction=reaction
    ).count()

    return jsonify({'count': count, 'toggled': existing is None})


@app.route('/challenge/<int:challenge_id>/comment', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def add_comment(challenge_id):
    user_id = session['user_id']
    message = request.form.get('message', '').strip()

    if not message:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('view_challenge', challenge_id=challenge_id))

    if len(message) > 500:
        flash('Comment is too long (500 character limit).', 'error')
        return redirect(url_for('view_challenge', challenge_id=challenge_id))

    if not ChallengeMember.query.filter_by(
        challenge_id=challenge_id, user_id=user_id
    ).first():
        flash('You are not a member of this challenge.', 'error')
        return redirect(url_for('dashboard'))

    comment = ChallengeComment(
        challenge_id=challenge_id,
        user_id=user_id,
        message=message
    )
    db.session.add(comment)
    db.session.commit()

    flash('Comment posted.', 'success')
    return redirect(url_for('view_challenge', challenge_id=challenge_id))


@app.route('/challenge/<int:challenge_id>/nudge/<int:target_user_id>', methods=['POST'])
@limiter.limit("20 per minute")
@login_required
def nudge_user(challenge_id, target_user_id):
    user_id = session['user_id']
    today = get_user_today()

    if target_user_id == user_id:
        return jsonify({'error': "Can't nudge yourself"}), 400

    sender_member = ChallengeMember.query.filter_by(
        challenge_id=challenge_id, user_id=user_id
    ).first()
    target_member = ChallengeMember.query.filter_by(
        challenge_id=challenge_id, user_id=target_user_id
    ).first()

    if not sender_member or not target_member:
        return jsonify({'error': 'Invalid member'}), 400

    already_checked = Checkin.query.filter_by(
        challenge_id=challenge_id, user_id=target_user_id, checkin_date=today
    ).first()
    if already_checked:
        return jsonify({'error': 'Already checked in'}), 400

    existing_nudge = Nudge.query.filter_by(
        challenge_id=challenge_id,
        from_user_id=user_id,
        to_user_id=target_user_id,
        nudge_date=today
    ).first()
    if existing_nudge:
        return jsonify({'error': 'Already nudged today'}), 400

    nudge = Nudge(
        challenge_id=challenge_id,
        from_user_id=user_id,
        to_user_id=target_user_id,
        nudge_date=today
    )
    db.session.add(nudge)

    challenge = Challenge.query.get(challenge_id)
    sender_name = session.get('display_name', 'Someone')

    create_notification(
        target_user_id,
        'nudge',
        'You got nudged!',
        f'{sender_name} nudged you to check in to "{challenge.name}". Don\'t break your streak!',
        url_for('view_challenge', challenge_id=challenge_id)
    )

    # Email nudge (placeholder until SendGrid/SMTP is configured)
    target_user = User.query.get(target_user_id)
    if target_user and target_user.email:
        logger.info(f'EMAIL TRIGGER: Nudge email to {target_user.email} - '
                     f'{sender_name} nudged them for "{challenge.name}"')
        # TODO: send_email(target_user.email, "Don't break your streak!", ...)

    db.session.commit()

    return jsonify({'success': True, 'message': 'Nudge sent!'})


@app.route('/explore')
@login_required
def explore():
    user_id = session['user_id']

    # Get user's current challenge IDs
    user_challenge_ids = [m.challenge_id for m in ChallengeMember.query.filter_by(user_id=user_id).all()]

    # Get public challenges the user hasn't joined
    query = Challenge.query.filter(
        Challenge.is_public == True,
        Challenge.is_completed == False
    )
    if user_challenge_ids:
        query = query.filter(~Challenge.id.in_(user_challenge_ids))

    challenges = query.order_by(Challenge.created_at.desc()).limit(20).all()

    return render_template('explore.html', challenges=challenges)


@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    user = User.query.get(user_id)

    # Calculate stats
    total_challenges = ChallengeMember.query.filter_by(user_id=user_id).count()
    total_points = db.session.query(db.func.sum(ChallengeMember.points)).filter_by(user_id=user_id).scalar() or 0
    best_streak = db.session.query(db.func.max(ChallengeMember.best_streak)).filter_by(user_id=user_id).scalar() or 0
    total_checkins = Checkin.query.filter_by(user_id=user_id).count()

    stats = {
        'total_challenges': total_challenges,
        'total_points': total_points,
        'best_streak': best_streak,
        'total_checkins': total_checkins,
    }

    # 30-day calendar
    today = get_user_today()
    thirty_days_ago = today - timedelta(days=30)

    checkin_history = db.session.query(
        Checkin.checkin_date,
        db.func.count(Checkin.id).label('count')
    ).filter(
        Checkin.user_id == user_id,
        Checkin.checkin_date >= thirty_days_ago
    ).group_by(Checkin.checkin_date).all()

    checkin_dates = {row.checkin_date: row.count for row in checkin_history}

    calendar_days = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        calendar_days.append({
            'date': day.isoformat(),
            'weekday': day.strftime('%a')[0],
            'day': day.day,
            'count': checkin_dates.get(day, 0),
            'is_today': day == today
        })

    # Weekly digest
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)

    this_week_checkins = Checkin.query.filter(
        Checkin.user_id == user_id,
        Checkin.checkin_date > week_ago
    ).count()

    last_week_checkins = Checkin.query.filter(
        Checkin.user_id == user_id,
        Checkin.checkin_date > two_weeks_ago,
        Checkin.checkin_date <= week_ago
    ).count()

    weekly_digest = {
        'checkins': this_week_checkins,
        'checkins_change': this_week_checkins - last_week_checkins,
        'checkin_rate': round(this_week_checkins / 7 * 100) if this_week_checkins else 0,
    }

    # Achievements
    achievements = db.session.query(Achievement, UserAchievement).join(
        UserAchievement, Achievement.id == UserAchievement.achievement_id
    ).filter(UserAchievement.user_id == user_id).order_by(
        UserAchievement.earned_at.desc()
    ).all()

    achievements = [{
        'name': a.Achievement.name,
        'description': a.Achievement.description,
        'icon': a.Achievement.icon,
        'earned_at': a.UserAchievement.earned_at,
    } for a in achievements]

    return render_template('profile.html',
                         user=user,
                         stats=stats,
                         calendar_days=calendar_days,
                         achievements=achievements,
                         weekly_digest=weekly_digest)


@app.route('/profile/edit', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def edit_profile():
    user_id = session['user_id']
    user = User.query.get(user_id)

    display_name = request.form.get('display_name', '').strip()
    user_timezone = validate_timezone(request.form.get('timezone', ''))

    if not display_name:
        flash('Display name cannot be empty.', 'error')
        return redirect(url_for('profile'))

    if len(display_name) > 50:
        flash('Display name is too long (50 character limit).', 'error')
        return redirect(url_for('profile'))

    user.display_name = display_name
    user.timezone = user_timezone
    db.session.commit()

    session['display_name'] = display_name
    session['timezone'] = user_timezone

    flash('Profile updated.', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/upload-photo', methods=['POST'])
@limiter.limit("5 per minute")
@login_required
def upload_profile_photo_route():
    user_id = session['user_id']

    if 'photo' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('profile'))

    photo = request.files['photo']
    if not photo or not photo.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('profile'))

    if not allowed_file(photo.filename):
        flash('Invalid file type. Use PNG, JPG, GIF, or WebP.', 'error')
        return redirect(url_for('profile'))

    if not validate_image_file(photo):
        flash('Uploaded file is not a valid image.', 'error')
        return redirect(url_for('profile'))

    if not cloudinary_configured:
        flash('Image uploads are not configured. Please contact support.', 'error')
        return redirect(url_for('profile'))

    photo_url = upload_profile_photo(photo, user_id)
    if not photo_url:
        flash('Failed to upload photo. Please try again.', 'error')
        return redirect(url_for('profile'))

    user = User.query.get(user_id)
    user.profile_photo = photo_url
    db.session.commit()

    session['profile_photo'] = photo_url

    flash('Profile photo updated.', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/remove-photo', methods=['POST'])
@login_required
def remove_profile_photo():
    user_id = session['user_id']
    user = User.query.get(user_id)

    # Note: We don't delete from Cloudinary to avoid complexity
    # Cloudinary's free tier has generous limits

    user.profile_photo = None
    db.session.commit()

    session.pop('profile_photo', None)

    flash('Profile photo removed.', 'success')
    return redirect(url_for('profile'))


@app.route('/achievements')
@login_required
def achievements_page():
    user_id = session['user_id']

    # Get all achievements with earned status
    all_achievements = db.session.query(
        Achievement,
        UserAchievement
    ).outerjoin(
        UserAchievement,
        (Achievement.id == UserAchievement.achievement_id) & (UserAchievement.user_id == user_id)
    ).order_by(
        UserAchievement.earned_at.desc().nulls_last(),
        Achievement.condition_value.asc()
    ).all()

    achievements = [{
        'name': a.Achievement.name,
        'description': a.Achievement.description,
        'icon': a.Achievement.icon,
        'condition_type': a.Achievement.condition_type,
        'condition_value': a.Achievement.condition_value,
        'earned': a.UserAchievement is not None,
        'earned_at': a.UserAchievement.earned_at if a.UserAchievement else None,
    } for a in all_achievements]

    earned_count = sum(1 for a in achievements if a['earned'])

    return render_template('achievements.html',
                         achievements=achievements,
                         earned_count=earned_count,
                         total_count=len(achievements))


@app.route('/notifications')
@login_required
def notifications_page():
    user_id = session['user_id']

    notifications = Notification.query.filter_by(user_id=user_id).order_by(
        Notification.created_at.desc()
    ).limit(50).all()

    # Mark all as read
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()

    return render_template('notifications.html', notifications=notifications)


@app.route('/api/challenge/<int:challenge_id>/leaderboard')
@login_required
def api_leaderboard(challenge_id):
    today = get_user_today()

    challenge = Challenge.query.get_or_404(challenge_id)

    leaderboard = []
    for m in challenge.members:
        checked_in_today = Checkin.query.filter_by(
            challenge_id=challenge_id, user_id=m.user_id, checkin_date=today
        ).first() is not None

        leaderboard.append({
            'display_name': m.user.display_name,
            'points': m.points,
            'current_streak': m.current_streak,
            'checked_in_today': checked_in_today,
        })

    leaderboard.sort(key=lambda x: -x['points'])
    return jsonify(leaderboard)


@app.route('/api/notifications/unread-count')
@login_required
def api_unread_count():
    count = Notification.query.filter_by(
        user_id=session['user_id'],
        is_read=False
    ).count()
    return jsonify({'count': count})


# --- Admin: Emergency Delete Check-in ---

def is_admin():
    """Check if current user is an admin. Set ADMIN_USERNAMES env var (comma-separated)."""
    admin_usernames = os.environ.get('ADMIN_USERNAMES', '').lower().split(',')
    return session.get('username', '').lower() in [u.strip() for u in admin_usernames if u.strip()]


@app.route('/admin/nuke/<int:checkin_id>', methods=['POST'])
@login_required
def nuke_checkin(checkin_id):
    if not is_admin():
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard'))

    checkin = Checkin.query.get_or_404(checkin_id)

    # Clean up reactions tied to this check-in
    CheckinReaction.query.filter_by(checkin_id=checkin_id).delete()

    db.session.delete(checkin)
    db.session.commit()

    logger.info(f'ADMIN: User {session["username"]} deleted checkin {checkin_id}')
    flash(f'Check-in {checkin_id} deleted.', 'success')
    return redirect(request.referrer or url_for('dashboard'))


# --- Error Handlers ---

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f'Internal server error: {e}')
    return render_template('500.html'), 500


@app.errorhandler(429)
def rate_limit_exceeded(e):
    flash('Too many requests. Please slow down.', 'error')
    return redirect(request.referrer or url_for('index'))


# --- Database Initialization ---

def init_app():
    """Initialize the database and seed data."""
    with app.app_context():
        db.create_all()
        seed_achievements()


# Auto-create tables only in local dev (FLASK_DEBUG=1)
# In production, use Flask-Migrate: flask db upgrade
if os.environ.get('FLASK_DEBUG') == '1':
    with app.app_context():
        db.create_all()
        seed_achievements()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
