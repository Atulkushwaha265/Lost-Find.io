from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os
import uuid
from config import Config
from forms_simple import LoginForm, RegisterForm
from security import validate_email

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student')
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    lost_items = db.relationship('LostItem', backref='reporter', lazy=True, cascade='all, delete-orphan')
    found_items = db.relationship('FoundItem', backref='finder', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LostItem(db.Model):
    __tablename__ = 'lost_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    location_lost = db.Column(db.String(200), nullable=False)
    date_lost = db.Column(db.Date, nullable=False)
    image_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    contact_info = db.Column(db.String(500))
    
    # Relationships
    matches = db.relationship('Match', foreign_keys='Match.lost_item_id', backref='lost_item', lazy=True)

class FoundItem(db.Model):
    __tablename__ = 'found_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)
    location_found = db.Column(db.String(200), nullable=False)
    date_found = db.Column(db.Date, nullable=False)
    image_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    contact_info = db.Column(db.String(500))
    storage_location = db.Column(db.String(200))
    
    # Relationships
    matches = db.relationship('Match', foreign_keys='Match.found_item_id', backref='found_item', lazy=True)

class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    lost_item_id = db.Column(db.Integer, db.ForeignKey('lost_items.id'), nullable=False)
    found_item_id = db.Column(db.Integer, db.ForeignKey('found_items.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verification_notes = db.Column(db.Text)
    match_score = db.Column(db.Numeric(3, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    verifier = db.relationship('User', backref='verified_matches')

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='info')
    is_read = db.Column(db.Boolean, default=False)
    related_item_type = db.Column(db.String(20))
    related_item_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return unique_filename
    return None

def calculate_match_score(lost_item, found_item):
    score = 0.0
    
    # Category match (40% weight)
    if lost_item.category.lower() == found_item.category.lower():
        score += 40.0
    
    # Name similarity (30% weight)
    lost_name = lost_item.item_name.lower()
    found_name = found_item.item_name.lower()
    if lost_name == found_name:
        score += 30.0
    elif lost_name in found_name or found_name in lost_name:
        score += 20.0
    else:
        # Simple word overlap
        lost_words = set(lost_name.split())
        found_words = set(found_name.split())
        overlap = len(lost_words & found_words)
        if overlap > 0:
            score += (overlap / max(len(lost_words), len(found_words))) * 30
    
    # Location similarity (20% weight)
    lost_loc = lost_item.location_lost.lower()
    found_loc = found_item.location_found.lower()
    if lost_loc == found_loc:
        score += 20.0
    elif lost_loc in found_loc or found_loc in lost_loc:
        score += 15.0
    else:
        # Check for common location words
        common_words = {'building', 'room', 'floor', 'lab', 'library', 'cafeteria', 'parking'}
        lost_words = set(lost_loc.split())
        found_words = set(found_loc.split())
        common_overlap = len((lost_words & found_words) & common_words)
        if common_overlap > 0:
            score += common_overlap * 5
    
    # Date proximity (10% weight)
    date_diff = abs((lost_item.date_lost - found_item.date_found).days)
    if date_diff <= 1:
        score += 10.0
    elif date_diff <= 3:
        score += 7.0
    elif date_diff <= 7:
        score += 5.0
    elif date_diff <= 14:
        score += 3.0
    
    return round(score, 2)

def create_notification(user_id, title, message, notification_type='info', related_item_type=None, related_item_id=None):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        related_item_type=related_item_type,
        related_item_id=related_item_id
    )
    db.session.add(notification)
    db.session.commit()

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        # Manual email validation
        if User.query.filter_by(email=form.email.data).first():
            flash('Email is already registered.', 'error')
            return render_template('register.html', form=form)
        
        user = User(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            role='student'
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    
    # Get user's items
    lost_items = LostItem.query.filter_by(user_id=current_user.id).order_by(LostItem.created_at.desc()).limit(5).all()
    found_items = FoundItem.query.filter_by(user_id=current_user.id).order_by(FoundItem.created_at.desc()).limit(5).all()
    
    # Get unread notifications
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
    
    # Get recent matches
    user_matches = []
    for lost_item in lost_items:
        for match in lost_item.matches:
            if match.status != 'rejected':
                user_matches.append(match)
    for found_item in found_items:
        for match in found_item.matches:
            if match.status != 'rejected':
                user_matches.append(match)

    unique_matches = list({match.id: match for match in user_matches}.values())
    unique_matches.sort(key=lambda x: x.created_at, reverse=True)

    return render_template('dashboard.html', 
                         lost_items=lost_items, 
                         found_items=found_items,
                         notifications=notifications,
                         matches=unique_matches[:5])

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Statistics
    total_lost = LostItem.query.count()
    total_found = FoundItem.query.count()
    total_matches = Match.query.count()
    pending_matches = Match.query.filter_by(status='pending').count()
    
    # Recent items
    recent_lost = LostItem.query.order_by(LostItem.created_at.desc()).limit(5).all()
    recent_found = FoundItem.query.order_by(FoundItem.created_at.desc()).limit(5).all()
    pending_matches_list = Match.query.filter_by(status='pending').order_by(Match.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_lost=total_lost,
                         total_found=total_found,
                         total_matches=total_matches,
                         pending_matches=pending_matches,
                         recent_lost=recent_lost,
                         recent_found=recent_found,
                         pending_matches_list=pending_matches_list)

# Lost Item Routes
@app.route('/lost-items')
@login_required
def lost_items():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = LostItem.query
    
    if search:
        query = query.filter(LostItem.item_name.ilike(f'%{search}%') | 
                           LostItem.description.ilike(f'%{search}%'))
    
    if category:
        query = query.filter(LostItem.category == category)
    
    if not current_user.is_admin():
        query = query.filter_by(user_id=current_user.id)
    
    items = query.order_by(LostItem.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    
    return render_template('lost_items.html', items=items, search=search, category=category)

@app.route('/report-lost-item', methods=['GET', 'POST'])
@login_required
def report_lost_item():
    from forms import LostItemForm
    
    form = LostItemForm()
    if form.validate_on_submit():
        image_filename = save_upload_file(form.image.data) if form.image.data else None
        
        lost_item = LostItem(
            user_id=current_user.id,
            item_name=form.item_name.data,
            description=form.description.data,
            category=form.category.data,
            location_lost=form.location_lost.data,
            date_lost=form.date_lost.data,
            image_url=image_filename,
            contact_info=form.contact_info.data
        )
        
        db.session.add(lost_item)
        db.session.commit()
        
        # Auto-match with found items
        found_items = FoundItem.query.filter_by(status='pending').all()
        for found_item in found_items:
            score = calculate_match_score(lost_item, found_item)
            if score >= 50.0:  # Threshold for auto-matching
                existing_match = Match.query.filter_by(
                    lost_item_id=lost_item.id, 
                    found_item_id=found_item.id
                ).first()
                
                if not existing_match:
                    match = Match(
                        lost_item_id=lost_item.id,
                        found_item_id=found_item.id,
                        match_score=score
                    )
                    db.session.add(match)
                    
                    # Notify admins about potential match
                    admin_users = User.query.filter_by(role='admin').all()
                    for admin in admin_users:
                        create_notification(
                            admin.id,
                            'New Potential Match',
                            f'A potential match has been found for "{lost_item.item_name}" with score {score}%',
                            'info',
                            'match',
                            match.id
                        )
        
        db.session.commit()
        
        flash('Lost item reported successfully!', 'success')
        return redirect(url_for('lost_items'))
    
    return render_template('report_lost_item.html', form=form)

# Found Item Routes
@app.route('/found-items')
@login_required
def found_items():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = FoundItem.query
    
    if search:
        query = query.filter(FoundItem.item_name.ilike(f'%{search}%') | 
                           FoundItem.description.ilike(f'%{search}%'))
    
    if category:
        query = query.filter(FoundItem.category == category)
    
    if not current_user.is_admin():
        query = query.filter_by(user_id=current_user.id)
    
    items = query.order_by(FoundItem.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    
    return render_template('found_items.html', items=items, search=search, category=category)

@app.route('/report-found-item', methods=['GET', 'POST'])
@login_required
def report_found_item():
    from forms import FoundItemForm
    
    form = FoundItemForm()
    if form.validate_on_submit():
        image_filename = save_upload_file(form.image.data) if form.image.data else None
        
        found_item = FoundItem(
            user_id=current_user.id,
            item_name=form.item_name.data,
            description=form.description.data,
            category=form.category.data,
            location_found=form.location_found.data,
            date_found=form.date_found.data,
            image_url=image_filename,
            contact_info=form.contact_info.data,
            storage_location=form.storage_location.data
        )
        
        db.session.add(found_item)
        db.session.commit()
        
        # Auto-match with lost items
        lost_items = LostItem.query.filter_by(status='pending').all()
        for lost_item in lost_items:
            score = calculate_match_score(lost_item, found_item)
            if score >= 50.0:  # Threshold for auto-matching
                existing_match = Match.query.filter_by(
                    lost_item_id=lost_item.id, 
                    found_item_id=found_item.id
                ).first()
                
                if not existing_match:
                    match = Match(
                        lost_item_id=lost_item.id,
                        found_item_id=found_item.id,
                        match_score=score
                    )
                    db.session.add(match)
                    
                    # Notify admins about potential match
                    admin_users = User.query.filter_by(role='admin').all()
                    for admin in admin_users:
                        create_notification(
                            admin.id,
                            'New Potential Match',
                            f'A potential match has been found for "{found_item.item_name}" with score {score}%',
                            'info',
                            'match',
                            match.id
                        )
        
        db.session.commit()
        
        flash('Found item reported successfully!', 'success')
        return redirect(url_for('found_items'))
    
    return render_template('report_found_item.html', form=form)

# Match Management Routes
@app.route('/matches')
@login_required
def matches():
    if current_user.is_admin():
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '')
        
        query = Match.query
        
        if status:
            query = query.filter(Match.status == status)
        
        matches_list = query.order_by(Match.match_score.desc(), Match.created_at.desc()).paginate(
            page=page, per_page=10, error_out=False)
        
        return render_template('admin/matches.html', matches=matches_list, status=status)
    else:
        # For students, show only their matches
        user_matches = []
        
        # Get lost items matches
        lost_items = LostItem.query.filter_by(user_id=current_user.id).all()
        for lost_item in lost_items:
            user_matches.extend(lost_item.matches)
        
        # Get found items matches
        found_items = FoundItem.query.filter_by(user_id=current_user.id).all()
        for found_item in found_items:
            user_matches.extend(found_item.matches)
        
        # Remove duplicates and sort
        unique_matches = list({match.id: match for match in user_matches}.values())
        unique_matches.sort(key=lambda x: x.created_at, reverse=True)
        
        return render_template('matches.html', matches=unique_matches)

@app.route('/match/<int:match_id>/update', methods=['POST'])
@login_required
def update_match(match_id):
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    match = Match.query.get_or_404(match_id)
    action = request.form.get('action')
    notes = request.form.get('verification_notes', '')
    
    if action == 'verify':
        match.status = 'verified'
        match.verified_by = current_user.id
        match.verification_notes = notes
        
        # Update item statuses
        match.lost_item.status = 'matched'
        match.found_item.status = 'matched'
        
        # Notify users
        create_notification(
            match.lost_item.user_id,
            'Item Match Verified!',
            f'Your lost item "{match.lost_item.item_name}" has been matched with a found item. Please contact the admin for verification.',
            'success',
            'match',
            match.id
        )
        
        create_notification(
            match.found_item.user_id,
            'Item Match Verified!',
            f'Your found item "{match.found_item.item_name}" has been matched with a lost item. Please contact the admin for verification.',
            'success',
            'match',
            match.id
        )
        
        flash('Match verified successfully!', 'success')
        
    elif action == 'reject':
        match.status = 'rejected'
        match.verification_notes = notes
        flash('Match rejected.', 'info')
    
    db.session.commit()
    return redirect(url_for('matches'))

@app.route('/item/<item_type>/<int:item_id>/mark-returned', methods=['POST'])
@login_required
def mark_item_returned(item_type, item_id):
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if item_type == 'lost':
        item = LostItem.query.get_or_404(item_id)
    elif item_type == 'found':
        item = FoundItem.query.get_or_404(item_id)
    else:
        flash('Invalid item type.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    item.status = 'returned'
    
    # Update related matches
    for match in item.matches:
        if match.status == 'verified':
            match.status = 'returned'
            
            # Notify users
            create_notification(
                match.lost_item.user_id,
                'Item Returned!',
                f'Your lost item "{match.lost_item.item_name}" has been returned.',
                'success',
                'match',
                match.id
            )
            
            create_notification(
                match.found_item.user_id,
                'Item Returned!',
                f'Your found item "{match.found_item.item_name}" has been returned to the owner.',
                'success',
                'match',
                match.id
            )
    
    db.session.commit()
    flash('Item marked as returned successfully!', 'success')
    
    if item_type == 'lost':
        return redirect(url_for('lost_items'))
    else:
        return redirect(url_for('found_items'))

# Notifications
@app.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifications_list = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    # Mark notifications as read
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notification in unread_notifications:
        notification.is_read = True
    db.session.commit()
    
    return render_template('notifications.html', notifications=notifications_list)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    
    if not name or not email or not validate_email(email):
        flash('Please enter a valid name and email.', 'error')
        return redirect(url_for('profile'))

    # Validate email uniqueness
    if email != current_user.email:
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'error')
            return redirect(url_for('profile'))
    
    current_user.name = name
    current_user.phone = phone
    current_user.email = email
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('profile'))
    
    if new_password != confirm_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('profile'))
    
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile'))

# Image serving
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# API endpoints for AJAX
@app.route('/api/search')
@login_required
def api_search():
    query = request.args.get('q', '')
    item_type = request.args.get('type', 'all')
    
    results = {'lost': [], 'found': []}
    
    if query:
        if item_type in ('lost', 'all'):
            lost_query = LostItem.query.filter(
                LostItem.item_name.ilike(f'%{query}%') | 
                LostItem.description.ilike(f'%{query}%')
            )
            if not current_user.is_admin():
                lost_query = lost_query.filter_by(user_id=current_user.id)
            lost_items = lost_query.limit(10).all()
            results['lost'] = [{'id': item.id, 'name': item.item_name, 'category': item.category} for item in lost_items]

        if item_type in ('found', 'all'):
            found_query = FoundItem.query.filter(
                FoundItem.item_name.ilike(f'%{query}%') | 
                FoundItem.description.ilike(f'%{query}%')
            )
            if not current_user.is_admin():
                found_query = found_query.filter_by(user_id=current_user.id)
            found_items = found_query.limit(10).all()
            results['found'] = [{'id': item.id, 'name': item.item_name, 'category': item.category} for item in found_items]
    
    return jsonify(results)

@app.route('/api/stats')
@login_required
def api_stats():
    if not current_user.is_admin():
        return jsonify({'error': 'Access denied'}), 403
    
    stats = {
        'total_lost': LostItem.query.count(),
        'total_found': FoundItem.query.count(),
        'total_matches': Match.query.count(),
        'pending_matches': Match.query.filter_by(status='pending').count(),
        'verified_matches': Match.query.filter_by(status='verified').count(),
        'returned_items': LostItem.query.filter_by(status='returned').count() + FoundItem.query.filter_by(status='returned').count()
    }
    
    return jsonify(stats)

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Failed to initialize database: {e}")
            raise
    app.run(host='0.0.0.0', debug=True)
