from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='student', nullable=False) # admin, faculty, student
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    announcements_authored = db.relationship('Announcement', foreign_keys='Announcement.author_id', backref='author', lazy='dynamic')
    courses_taught = db.relationship('Course', foreign_keys='Course.faculty_id', backref='faculty_instructor', lazy='dynamic')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

    # Flask-Login integration
    def get_id(self):
       return str(self.id)

    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_faculty(self):
        return self.role == 'faculty'

    @property
    def is_student(self):
        return self.role == 'student'


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Can be admin or faculty

    def __repr__(self):
        return f'<Announcement {self.title}>'


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Faculty teaching the course

    def __repr__(self):
        return f'<Course {self.code}: {self.title}>'

# Potential future models: Enrollment, Assignment, Submission, Grade