from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse # Corrected import
from functools import wraps # For role-based decorators
from datetime import datetime
import os

# --- Configuration ---
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-hard-to-guess-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# --- Application Setup ---
app = Flask(__name__)
app.config.from_object(Config)

# --- Database Setup (models are now in this file for simplicity for a single file request) ---
db = SQLAlchemy(app)

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

    def get_id(self): # Required by Flask-Login
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
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Announcement {self.title}>'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return f'<Course {self.code}: {self.title}>'

# --- Forms Setup (forms are now in this file for simplicity) ---
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=128)])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    role = SelectField('Role', choices=[('student', 'Student'), ('faculty', 'Faculty'), ('admin', 'Admin')],
                       default='student', validators=[DataRequired()]) # Used by admin_create_user
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class AnnouncementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post Announcement')

class CourseForm(FlaskForm):
    title = StringField('Course Title', validators=[DataRequired(), Length(max=100)])
    code = StringField('Course Code', validators=[DataRequired(), Length(max=20)])
    description = TextAreaField('Description')
    faculty_id = SelectField('Assign Faculty', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Course')


# --- Flask-Login Setup ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.login_message = "Please log in to access this page."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Context Processor for Year in Footer ---
@app.context_processor
def inject_now():
    return {'current_year': datetime.utcnow().year}

# --- Custom Decorators for Role-Based Access ---
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required for this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def faculty_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Admins can also access faculty areas
        if not (current_user.is_faculty or current_user.is_admin):
            flash('Faculty or Admin access required for this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
@app.route('/index')
def index():
    latest_announcements = Announcement.query.order_by(Announcement.timestamp.desc()).limit(3).all()
    return render_template('index.html', title='Welcome', announcements=latest_announcements)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '': # Corrected usage
            next_page = url_for('dashboard')
        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    # Remove role field from public registration form instance, or ensure it's handled safely
    del form.role # Simplest way to prevent public role setting

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role='student') # Default role
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Congratulations, {user.username}, your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Create an Account', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return render_template('dashboard.html', title='Admin Dashboard')
    elif current_user.is_faculty:
        my_courses = Course.query.filter_by(faculty_id=current_user.id).all()
        return render_template('dashboard.html', title='Faculty Dashboard', my_courses=my_courses)
    else: # Student
        all_courses = Course.query.all()
        return render_template('dashboard.html', title='Student Dashboard', courses=all_courses)

# --- Admin Routes ---
@app.route('/admin/users')
@admin_required
def admin_user_list():
    users = User.query.order_by(User.username).all()
    return render_template('admin/user_list.html', title='Manage Users', users=users)

@app.route('/admin/create_user', methods=['GET', 'POST'])
@admin_required
def admin_create_user():
    form = RegistrationForm() # Uses the full RegistrationForm with the role field
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.username} ({user.role}) created successfully!', 'success')
        return redirect(url_for('admin_user_list'))
    return render_template('admin/create_user.html', title='Create New User', form=form, legend='Create New User')

# --- Faculty & Admin: Announcements Management ---
@app.route('/announcements/manage')
@faculty_required
def manage_announcements():
    if current_user.is_admin:
        announcements = Announcement.query.order_by(Announcement.timestamp.desc()).all()
    else: # Faculty
        announcements = Announcement.query.filter_by(author_id=current_user.id).order_by(Announcement.timestamp.desc()).all()
    return render_template('faculty/manage_announcements.html', title='Manage Announcements', announcements=announcements)

@app.route('/announcements/new', methods=['GET', 'POST'])
@faculty_required
def create_announcement():
    form = AnnouncementForm()
    if form.validate_on_submit():
        announcement = Announcement(title=form.title.data, content=form.content.data, author_id=current_user.id)
        db.session.add(announcement)
        db.session.commit()
        flash('Announcement created!', 'success')
        return redirect(url_for('manage_announcements'))
    return render_template('faculty/create_edit_announcement.html', title='New Announcement', form=form, legend='New Announcement')

@app.route('/announcements/<int:announcement_id>/edit', methods=['GET', 'POST'])
@faculty_required
def edit_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    if announcement.author_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this announcement.', 'danger')
        return redirect(url_for('manage_announcements'))
    
    form = AnnouncementForm(obj=announcement)
    if form.validate_on_submit():
        announcement.title = form.title.data
        announcement.content = form.content.data
        db.session.commit()
        flash('Announcement updated!', 'success')
        return redirect(url_for('manage_announcements'))
    return render_template('faculty/create_edit_announcement.html', title='Edit Announcement', form=form, legend='Edit Announcement')

@app.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@faculty_required
def delete_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    if announcement.author_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to delete this announcement.', 'danger')
        return redirect(url_for('manage_announcements'))
    db.session.delete(announcement)
    db.session.commit()
    flash('Announcement deleted.', 'success')
    return redirect(url_for('manage_announcements'))

# --- Faculty & Admin: Courses Management ---
@app.route('/courses/manage')
@faculty_required
def manage_courses():
    if current_user.is_admin:
        courses = Course.query.order_by(Course.title).all()
    else: # Faculty
        courses = Course.query.filter_by(faculty_id=current_user.id).order_by(Course.title).all()
    return render_template('faculty/manage_courses.html', title='Manage Courses', courses=courses)

@app.route('/courses/new', methods=['GET', 'POST'])
@faculty_required # Or @admin_required if only admins create courses
def create_course():
    form = CourseForm()
    form.faculty_id.choices = [(f.id, f.username) for f in User.query.filter_by(role='faculty').all()]
    if not form.faculty_id.choices: # Handle case where no faculty exist
         form.faculty_id.choices.insert(0, (0, 'No Faculty Available - Create Faculty First')) # Placeholder
    
    if request.method == 'POST' and form.validate_on_submit(): # Check for POST specifically for validation
        course_exists = Course.query.filter_by(code=form.code.data).first()
        if course_exists:
            flash('A course with this code already exists.', 'warning')
        else:
            # Ensure faculty_id is valid or handle if no faculty selected
            selected_faculty_id = form.faculty_id.data
            if selected_faculty_id == 0 and not User.query.filter_by(role='faculty').all(): # if placeholder was selected
                flash('Cannot create course. Please create faculty users first or assign a valid faculty.', 'danger')
            else:
                course = Course(title=form.title.data, code=form.code.data, 
                                description=form.description.data, faculty_id=selected_faculty_id)
                db.session.add(course)
                db.session.commit()
                flash('Course created!', 'success')
                return redirect(url_for('manage_courses'))
    elif request.method == 'POST': # Log form errors if POST and not valid
        flash('There was an error with your submission. Please check the fields.', 'danger')
        for field, errors in form.errors.items():
            for error in errors:
                app.logger.error(f"Error in {getattr(form, field).label.text}: {error}")


    return render_template('faculty/create_edit_course.html', title='New Course', form=form, legend='New Course')


@app.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@faculty_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course.faculty_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('manage_courses'))

    form = CourseForm(obj=course)
    form.faculty_id.choices = [(f.id, f.username) for f in User.query.filter_by(role='faculty').all()]
    if not form.faculty_id.choices:
         form.faculty_id.choices.insert(0, (0, 'No Faculty Available'))

    if form.validate_on_submit():
        if form.code.data != course.code:
            existing_course = Course.query.filter(Course.id != course.id, Course.code == form.code.data).first()
            if existing_course:
                flash('Another course with this code already exists.', 'warning')
                return render_template('faculty/create_edit_course.html', title='Edit Course', form=form, legend='Edit Course', course=course)
        
        selected_faculty_id = form.faculty_id.data
        if selected_faculty_id == 0 and not User.query.filter_by(role='faculty').all() and course.faculty_id is not None: # if placeholder was selected
            flash('Cannot update course to "No Faculty Available" if faculty existed. Assign a valid faculty or keep current.', 'danger')
        else:
            course.title = form.title.data
            course.code = form.code.data
            course.description = form.description.data
            course.faculty_id = selected_faculty_id if selected_faculty_id != 0 else course.faculty_id # Keep current if 0 selected and faculty exist
            db.session.commit()
            flash('Course updated!', 'success')
            return redirect(url_for('manage_courses'))
    elif request.method == 'POST': # Log form errors if POST and not valid
        flash('There was an error with your submission. Please check the fields.', 'danger')
        for field, errors in form.errors.items():
            for error in errors:
                app.logger.error(f"Error in {getattr(form, field).label.text}: {error}")


    return render_template('faculty/create_edit_course.html', title='Edit Course', form=form, legend='Edit Course', course=course)


@app.route('/courses/<int:course_id>/delete', methods=['POST'])
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted.', 'success')
    return redirect(url_for('manage_courses'))

# --- Student Routes ---
@app.route('/student/announcements')
@login_required
def student_view_announcements():
    announcements = Announcement.query.order_by(Announcement.timestamp.desc()).all()
    return render_template('student/view_announcements.html', title='Announcements', announcements=announcements)

@app.route('/student/courses')
@login_required
def student_view_courses():
    courses = Course.query.order_by(Course.title).all()
    return render_template('student/view_courses.html', title='Available Courses', courses=courses)


# --- CLI commands for DB and initial setup ---
@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    db.drop_all()
    db.create_all()
    print("Initialized the database.")
    # You might want to call create_admin_command here automatically if it makes sense for your workflow
    # create_admin_command.callback() # Call the function directly

@app.cli.command("create-admin")
def create_admin_command():
    """Create a default admin user and sample users."""
    if User.query.filter_by(username='admin').first():
        print("Admin user 'admin' already exists.")
    else:
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('adminpass') # CHANGE THIS IN PRODUCTION
        db.session.add(admin)
        print("Admin user 'admin' created with password 'adminpass'.")

    if User.query.filter_by(username='prof_smith').first():
        print("Faculty user 'prof_smith' already exists.")
    else:
        faculty_user = User(username='prof_smith', email='smith@example.com', role='faculty')
        faculty_user.set_password('facultypass') # CHANGE THIS
        db.session.add(faculty_user)
        print("Faculty user 'prof_smith' created with password 'facultypass'.")

    if User.query.filter_by(username='john_doe').first():
        print("Student user 'john_doe' already exists.")
    else:
        student_user = User(username='john_doe', email='john@example.com', role='student')
        student_user.set_password('studentpass') # CHANGE THIS
        db.session.add(student_user)
        print("Student user 'john_doe' created with password 'studentpass'.")
    
    db.session.commit()
    print("Users committed to the database.")

if __name__ == '__main__':
    # For development:
    # 1. In your terminal, navigate to the project directory.
    # 2. Set FLASK_APP environment variable:
    #    Linux/macOS: export FLASK_APP=app.py
    #    Windows CMD:   set FLASK_APP=app.py
    #    Windows PowerShell: $env:FLASK_APP = "app.py"
    # 3. (Optional, for debug mode) Set FLASK_ENV:
    #    Linux/macOS: export FLASK_ENV=development
    #    Windows CMD:   set FLASK_ENV=development
    #    Windows PowerShell: $env:FLASK_ENV = "development"
    # 4. Initialize database (run once, or after model changes and you want to reset):
    #    flask init-db
    # 5. Create admin user (run once):
    #    flask create-admin
    # 6. Run the app:
    #    flask run
    #    OR
    app.run(debug=True) # debug=True is good for development