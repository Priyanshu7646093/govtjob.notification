import os
import json
import datetime
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import config
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect 

app = Flask(__name__)
app.config.from_object(config['development'])
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'
csrf = CSRFProtect(app)  # Initialize CSRF protection

# Models
class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    education_level = db.Column(db.String(50), nullable=False)
    syllabus_text = db.Column(db.Text)
    syllabus_pdf = db.Column(db.String(255))
    cutoff_data = db.Column(db.Text)
    eligibility = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    selection_process = db.Column(db.Text)
    notification_link = db.Column(db.String(255))
    apply_link = db.Column(db.String(255))
    exam_date = db.Column(db.Date)
    vacancies = db.Column(db.Integer)
    salary = db.Column(db.String(100))
    locations = db.Column(db.Text, nullable=False)
    fees = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(255), nullable=False)
    source_link = db.Column(db.String(255), nullable=False)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending', index=True)
    processed_at = db.Column(db.DateTime)
    processed_by = db.Column(db.Integer, db.ForeignKey('admin.id'))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    saved_jobs = db.relationship('SavedJob', backref='user', lazy=True)

class SavedJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

# Login Manager
@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# Context processor to inject variables into all templates
@app.context_processor
def inject_variables():
    return {
        'now': datetime.utcnow(),
        'current_year': datetime.utcnow().year
    }

# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route('/')
def index():
    jobs = Job.query.order_by(Job.created_at.desc()).limit(10).all()
    return render_template('index.html', jobs=jobs)

@app.route('/job/<int:job_id>')
def job_detail(job_id):
    try:
        job = Job.query.get_or_404(job_id)
        today = datetime.utcnow().date()
        return render_template('job_detail.html', job=job, today=today)
    except Exception as e:
        flash('Error loading job details', 'error')
        return redirect(url_for('index'))

# Admin Login Page
@app.route('/admin/login', methods=['GET'])
def admin_login_page():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin/login.html')

# Admin Login Action
@app.route('/admin/login', methods=['POST'])
def admin_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    admin = Admin.query.filter_by(username=username).first()
    
    if admin and check_password_hash(admin.password, password):
        login_user(admin)
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid credentials', 'danger')
        return redirect(url_for('admin_login_page'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    suggestions = Suggestion.query.filter_by(status='Pending').all()
    return render_template(
        'admin/dashboard.html', 
        jobs=jobs, 
        suggestions=suggestions,
        datetime=datetime
    )

@app.route('/admin/job/new', methods=['GET', 'POST'])
@login_required
def new_job():
    if request.method == 'POST':
        # Extract form data
        data = request.form
        files = request.files
        
        # Handle file upload
        syllabus_pdf = None
        if 'syllabus_pdf' in files and files['syllabus_pdf'].filename != '':
            file = files['syllabus_pdf']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                syllabus_pdf = filename
        
        # Prepare fees JSON
        fees = {
            "General": data.get('fee_general'),
            "SC": data.get('fee_sc'),
            "ST": data.get('fee_st'),
            "OBC": data.get('fee_obc')
        }
        
        # Create new job
        job = Job(
            title=data['title'],
            department=data['department'],
            education_level=data['education_level'],
            syllabus_text=data['syllabus_text'],
            syllabus_pdf=syllabus_pdf,
            cutoff_data=data['cutoff_data'],
            eligibility=data['eligibility'],
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d'),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d'),
            selection_process=data['selection_process'],
            notification_link=data['notification_link'],
            apply_link=data['apply_link'],
            exam_date=datetime.strptime(data['exam_date'], '%Y-%m-%d') if data['exam_date'] else None,
            vacancies=data['vacancies'],
            salary=data['salary'],
            locations=data['locations'],
            fees=fees
        )
        
        db.session.add(job)
        db.session.commit()
        
        flash('Job created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/job_form.html')

@app.route('/admin/job/edit/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    
    if request.method == 'POST':
        data = request.form
        files = request.files
        
        # Handle file upload
        if 'syllabus_pdf' in files and files['syllabus_pdf'].filename != '':
            file = files['syllabus_pdf']
            if file and allowed_file(file.filename):
                # Remove old file if exists
                if job.syllabus_pdf:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], job.syllabus_pdf))
                    except:
                        pass
                # Save new file
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                job.syllabus_pdf = filename
        
        # Update fields
        job.title = data['title']
        job.department = data['department']
        job.education_level = data['education_level']
        job.syllabus_text = data['syllabus_text']
        job.cutoff_data = data['cutoff_data']
        job.eligibility = data['eligibility']
        job.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
        job.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
        job.selection_process = data['selection_process']
        job.notification_link = data['notification_link']
        job.apply_link = data['apply_link']
        job.exam_date = datetime.strptime(data['exam_date'], '%Y-%m-%d') if data['exam_date'] else None
        job.vacancies = data['vacancies']
        job.salary = data['salary']
        job.locations = data['locations']
        job.fees = {
            "General": data.get('fee_general'),
            "SC": data.get('fee_sc'),
            "ST": data.get('fee_st'),
            "OBC": data.get('fee_obc')
        }
        
        db.session.commit()
        flash('Job updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/job_form.html', job=job)

@app.route('/admin/job/delete/<int:job_id>')
@login_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Delete associated file
    if job.syllabus_pdf:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], job.syllabus_pdf))
        except:
            pass
    
    db.session.delete(job)
    db.session.commit()
    
    flash('Job deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve-suggestion/<int:suggestion_id>', methods=['POST'])
@login_required
def approve_suggestion(suggestion_id):
    suggestion = Suggestion.query.get_or_404(suggestion_id)
    suggestion.status = 'Approved'
    suggestion.processed_at = datetime.utcnow()
    suggestion.processed_by = current_user.id
    db.session.commit()

    flash('Suggestion approved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject-suggestion/<int:suggestion_id>', methods=['POST'])
@login_required
def reject_suggestion(suggestion_id):
    suggestion = Suggestion.query.get_or_404(suggestion_id)
    suggestion.status = 'Rejected'
    suggestion.processed_at = datetime.utcnow()
    suggestion.processed_by = current_user.id
    db.session.commit()
    
    flash('Suggestion rejected successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# Add this new route to view suggestion details
@app.route('/admin/suggestion/<int:suggestion_id>')
@login_required
def view_suggestion(suggestion_id):
    suggestion = Suggestion.query.get_or_404(suggestion_id)
    return render_template('admin/suggestion_detail.html', suggestion=suggestion)

@app.template_filter('time_ago')
def time_ago(dt):
    now = datetime.utcnow()
    diff = now - dt
    
    if diff < timedelta(minutes=1):
        return 'just now'
    elif diff < timedelta(hours=1):
        return f'{int(diff.seconds / 60)} minutes ago'
    elif diff < timedelta(days=1):
        return f'{int(diff.seconds / 3600)} hours ago'
    elif diff < timedelta(days=30):
        return f'{diff.days} days ago'
    else:
        return dt.strftime('%Y-%m-%d')

@app.route('/suggest', methods=['GET', 'POST'])
def suggest_job():
    if request.method == 'POST':
        suggestion = Suggestion(
            job_title=request.form['title'],
            source_link=request.form['link'],
            comments=request.form['comments']
        )
        db.session.add(suggestion)
        db.session.commit()
        flash('Thank you for your suggestion! We will review it soon.', 'success')
        return redirect(url_for('index'))
    return render_template('suggest.html')

@app.route('/api/jobs')
def api_jobs():
    # Get filter parameters
    education = request.args.get('education', 'all')
    department = request.args.get('department', 'all')
    location = request.args.get('location', '')
    page = int(request.args.get('page', 1))
    per_page = 10
    
    # Build query
    query = Job.query
    
    if education != 'all':
        query = query.filter_by(education_level=education)
    
    if department != 'all':
        query = query.filter_by(department=department)
    
    if location:
        query = query.filter(Job.locations.ilike(f'%{location}%'))
    
    # Pagination
    jobs = query.order_by(Job.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # Prepare response
    job_list = []
    for job in jobs.items:
        job_list.append({
            'id': job.id,
            'title': job.title,
            'department': job.department,
            'education_level': job.education_level,
            'end_date': job.end_date.strftime('%Y-%m-%d'),
            'locations': job.locations,
            'days_left': (job.end_date - datetime.utcnow().date()).days
        })
    
    return jsonify({
        'jobs': job_list,
        'total_pages': jobs.pages,
        'current_page': page
    })

@app.route('/save-job/<int:job_id>', methods=['POST'])
def save_job(job_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Login required'}), 401
    
    # Check if already saved
    existing = SavedJob.query.filter_by(user_id=current_user.id, job_id=job_id).first()
    if existing:
        return jsonify({'error': 'Job already saved'}), 400
    
    # Save job
    saved_job = SavedJob(user_id=current_user.id, job_id=job_id)
    db.session.add(saved_job)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True)