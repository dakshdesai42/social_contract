"""
SQLAlchemy Models for Social Contract
Replaces raw SQL with proper ORM models for safer database operations
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)  # Nullable for OAuth users
    display_name = db.Column(db.String(120))
    google_id = db.Column(db.String(128), unique=True, nullable=True, index=True)
    email = db.Column(db.String(254), unique=True, nullable=True, index=True)
    profile_photo = db.Column(db.String(512))  # Now stores Cloudinary URL
    total_points = db.Column(db.Integer, default=0)
    timezone = db.Column(db.String(64), default='UTC')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    challenges_created = db.relationship('Challenge', back_populates='creator', foreign_keys='Challenge.creator_id')
    memberships = db.relationship('ChallengeMember', back_populates='user', cascade='all, delete-orphan')
    checkins = db.relationship('Checkin', back_populates='user', cascade='all, delete-orphan')
    achievements = db.relationship('UserAchievement', back_populates='user', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan')
    comments = db.relationship('ChallengeComment', back_populates='user', cascade='all, delete-orphan')
    reactions = db.relationship('CheckinReaction', back_populates='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'


class Challenge(db.Model):
    __tablename__ = 'challenges'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    join_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    is_public = db.Column(db.Boolean, default=False)
    points_per_checkin = db.Column(db.Integer, default=10)
    penalty_per_miss = db.Column(db.Integer, default=5)
    streak_bonus = db.Column(db.Integer, default=5)
    verification_type = db.Column(db.String(20), default='none')  # none, photo_optional, photo_required
    end_date = db.Column(db.Date, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    milestone_target = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    creator = db.relationship('User', back_populates='challenges_created', foreign_keys=[creator_id])
    winner = db.relationship('User', foreign_keys=[winner_id])
    members = db.relationship('ChallengeMember', back_populates='challenge', cascade='all, delete-orphan')
    checkins = db.relationship('Checkin', back_populates='challenge', cascade='all, delete-orphan')
    comments = db.relationship('ChallengeComment', back_populates='challenge', cascade='all, delete-orphan')
    nudges = db.relationship('Nudge', back_populates='challenge', cascade='all, delete-orphan')

    @property
    def member_count(self):
        return len(self.members)

    def __repr__(self):
        return f'<Challenge {self.name}>'


class ChallengeMember(db.Model):
    __tablename__ = 'challenge_members'
    __table_args__ = (
        db.UniqueConstraint('challenge_id', 'user_id', name='uq_challenge_member'),
    )

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    points = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    best_streak = db.Column(db.Integer, default=0)
    streak_freezes = db.Column(db.Integer, default=0)
    freezes_used = db.Column(db.Integer, default=0)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    challenge = db.relationship('Challenge', back_populates='members')
    user = db.relationship('User', back_populates='memberships')

    def __repr__(self):
        return f'<ChallengeMember user={self.user_id} challenge={self.challenge_id}>'


class Checkin(db.Model):
    __tablename__ = 'checkins'
    __table_args__ = (
        db.UniqueConstraint('challenge_id', 'user_id', 'checkin_date', name='uq_checkin_daily'),
        db.Index('idx_checkins_user_date', 'user_id', 'checkin_date'),
        db.Index('idx_checkins_challenge', 'challenge_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    checkin_date = db.Column(db.Date, nullable=False)
    note = db.Column(db.Text)
    photo_url = db.Column(db.String(512))  # Cloudinary URL instead of local filename
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    challenge = db.relationship('Challenge', back_populates='checkins')
    user = db.relationship('User', back_populates='checkins')
    reactions = db.relationship('CheckinReaction', back_populates='checkin', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Checkin user={self.user_id} date={self.checkin_date}>'


class CheckinReaction(db.Model):
    __tablename__ = 'checkin_reactions'
    __table_args__ = (
        db.UniqueConstraint('checkin_id', 'user_id', 'reaction', name='uq_checkin_reaction'),
        db.Index('idx_reactions_checkin', 'checkin_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    checkin_id = db.Column(db.Integer, db.ForeignKey('checkins.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reaction = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    checkin = db.relationship('Checkin', back_populates='reactions')
    user = db.relationship('User', back_populates='reactions')


class Achievement(db.Model):
    __tablename__ = 'achievements'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(20), default='')
    condition_type = db.Column(db.String(50), nullable=False)
    condition_value = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user_achievements = db.relationship('UserAchievement', back_populates='achievement')

    def __repr__(self):
        return f'<Achievement {self.name}>'


class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', back_populates='achievements')
    achievement = db.relationship('Achievement', back_populates='user_achievements')


class Notification(db.Model):
    __tablename__ = 'notifications'
    __table_args__ = (
        db.Index('idx_notifications_user_read', 'user_id', 'is_read'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', back_populates='notifications')


class ChallengeComment(db.Model):
    __tablename__ = 'challenge_comments'
    __table_args__ = (
        db.Index('idx_comments_challenge', 'challenge_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    challenge = db.relationship('Challenge', back_populates='comments')
    user = db.relationship('User', back_populates='comments')


class Nudge(db.Model):
    __tablename__ = 'nudges'
    __table_args__ = (
        db.UniqueConstraint('challenge_id', 'from_user_id', 'to_user_id', 'nudge_date', name='uq_nudge_daily'),
    )

    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nudge_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    challenge = db.relationship('Challenge', back_populates='nudges')
    from_user = db.relationship('User', foreign_keys=[from_user_id])
    to_user = db.relationship('User', foreign_keys=[to_user_id])


def seed_achievements():
    """Seed default achievements if table is empty."""
    if Achievement.query.count() == 0:
        achievements = [
            Achievement(name='First Check-in', description='Complete your first daily check-in',
                       icon='&#9989;', condition_type='total_checkins', condition_value=1),
            Achievement(name='Week Warrior', description='Reach a 7-day streak',
                       icon='&#128293;', condition_type='streak', condition_value=7),
            Achievement(name='Month Master', description='Reach a 30-day streak',
                       icon='&#11088;', condition_type='streak', condition_value=30),
            Achievement(name='Unstoppable', description='Reach a 50-day streak',
                       icon='&#9889;', condition_type='streak', condition_value=50),
            Achievement(name='Centurion', description='Earn 100 total points',
                       icon='&#127942;', condition_type='total_points', condition_value=100),
            Achievement(name='Point Machine', description='Earn 500 total points',
                       icon='&#128176;', condition_type='total_points', condition_value=500),
            Achievement(name='Social Butterfly', description='Join 3 different challenges',
                       icon='&#129309;', condition_type='challenges_joined', condition_value=3),
            Achievement(name='Challenge Creator', description='Create your first challenge',
                       icon='&#9876;&#65039;', condition_type='challenges_created', condition_value=1),
            Achievement(name='Photographer', description='Submit 10 photo proof check-ins',
                       icon='&#128247;', condition_type='photo_checkins', condition_value=10),
        ]
        db.session.add_all(achievements)
        db.session.commit()
