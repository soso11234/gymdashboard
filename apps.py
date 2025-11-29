import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, date
import sys
import logging
from functools import wraps
from app.Member_Service import register_member

# Assuming db_init provides the initialization function
try:
    from db_init import initialize
except ImportError:
    # Placeholder if db_init.py is not provided, assumes initialization happens elsewhere or is stubbed
    def initialize():
        print("Warning: db_init.py or initialize() not found. Database setup might be skipped.")

# --- Setup logging and Path ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Ensure service files are importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- Import Service functions ---
try:
    # Member Service Imports
    from app.Member_Service import register_member, check_member, update_member_goal
    # Admin Service Imports
    from app.Admin_Service import register_trainer, update_invoice
    # Trainer Service Imports
    from app.Trainer_Service import update_trainer_availability, view_trainer_schedule
except ImportError as e:
    logger.error(f"FATAL: Failed to import service module. Check file names and function definitions: {e}")
    # Define placeholder functions to avoid application crash during startup
    def register_member(*args, **kwargs): return None
    def login_user(*args, **kwargs): return {'id': 1, 'role': 'admin'} # Default admin for testing if login fails
    def enroll_in_class(*args, **kwargs): return False
    def log_health_metric(*args, **kwargs): return False
    def update_member_goal(*args, **kwargs): return False
    def cancel_class_enrollment(*args, **kwargs): return False
    def register_trainer(*args, **kwargs): return None
    def create_class(*args, **kwargs): return None
    def update_invoice(*args, **kwargs): return False
    def add_equipment(*args, **kwargs): return None
    def log_equipment_maintenance(*args, **kwargs): return False
    def remove_class(*args, **kwargs): return False
    def update_trainer_availability(*args, **kwargs): return False
    def view_trainer_schedule(*args, **kwargs): return {}
    def view_class_roster(*args, **kwargs): return []

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_session_management')


# --- Decorators for Role-Based Access Control (RBAC) ---

def login_required(f):
    """Decorator to protect routes that require a logged-in user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('show_login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """Decorator to enforce specific user roles."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if session.get('user_role') != required_role:
                flash(f'Access denied. You must be a {required_role}.', 'error')
                # Redirect to their own dashboard or login page
                if session.get('user_role'):
                    return redirect(url_for(f"{session.get('user_role')}_dashboard"))
                return redirect(url_for('show_login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- Public Routes (Login/Logout/Register) ---

@app.route('/')
def index():
    return redirect(url_for('show_login'))

# IMPORTANT: Ensure the URL for the login form in log_in.html targets '/api/login'
@app.route('/login', methods=['GET'])
def show_login():
    return render_template('log_in.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    email = request.form.get('email')
    password = request.form.get('password')
    print(email)
    print(password)

    
    user_data = login_user(email=email, password=password) # Should return {'id': int, 'role': str} or None
    print(user_data)
    if user_data:
        session['user_id'] = user_data['id']
        session['user_role'] = user_data['role']
        flash(f'Welcome back!', 'success')
        
        # Use direct URL for dashboard redirection based on role
        if user_data['role'] == 'member':
            return redirect(url_for('member_dashboard'))
        elif user_data['role'] == 'trainer':
            return redirect(url_for('trainer_dashboard'))
        elif user_data['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
    """
    if check_member(email, password):
        return redirect(url_for('member_dashboard'))
    else:
        print("ERORRRRRRRR")
    flash('Invalid email or password.', 'error')
    """
    return redirect(url_for('show_login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('show_login'))

@app.route('/register', methods=['GET'])
def show_registration():
    return render_template('registration.html')

# The original registration route is kept for member registration
@app.route('/api/register', methods=['POST'])
def api_register():
    # This function is retained from the previous version for member registration
    try:
        data = request.form
        required_fields = ['name', 'email', 'password', 'phone', 'dob', 'gender', 'height', 'weight', 'heart_rate', 'goals']
        if not all(field in data for field in required_fields):
            flash('All fields are required.', 'error')
            return redirect(url_for('show_registration'))

        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        phone = data.get('phone')
        dob_str = data.get('dob')
        gender = data.get('gender')
        
        try:
            height = float(data.get('height'))
            weight = float(data.get('weight'))
            heart_rate = int(data.get('heart_rate'))
            goals = data.get('goals')
            date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            register_member(name,email,date_of_birth,password,phone)
        except ValueError:
            flash('Invalid format for date, height, weight, or heart rate.', 'error')
            return redirect(url_for('show_registration'))

        member_id = register_member(
            name=name, email=email, password=password, phone=phone, date_of_birth=date_of_birth,
            gender=gender, initial_weight_kg=weight, initial_height_cm=height,
            initial_heart_rate_bpm=heart_rate, initial_goal_description=goals
        )
        
        if member_id:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('show_login'))
        else:
            flash('Registration failed. This email may already be registered, or a system error occurred.', 'error')
            return redirect(url_for('show_registration'))

    except Exception as e:
        logger.error(f"Member Registration Error: {e}", exc_info=True)
        flash(f'An internal error occurred during registration. Please try again.', 'error')
        return redirect(url_for('show_registration'))


# --- Dashboard Routes ---

@app.route('/dashboard/member', methods=['GET'])
@role_required('member')
def member_dashboard():
    member_id = session.get('user_id')
    # TODO: Fetch comprehensive dashboard data (metrics, goals, classes, etc.)
    return render_template('member dash.html', user_id=member_id, user_role='member')


@app.route('/dashboard/trainer', methods=['GET'])
@role_required('trainer')
def trainer_dashboard():
    trainer_id = session.get('user_id')
    # TODO: Fetch today's schedule, class rosters, etc.
    return render_template('trainer dash.html', user_id=trainer_id, user_role='trainer')


@app.route('/dashboard/admin', methods=['GET'])
@role_required('admin')
def admin_dashboard():
    admin_id = session.get('user_id')
    # TODO: Fetch overview stats (active members, classes, equipment status)
    return render_template('admin dash.html', user_id=admin_id, user_role='admin')


# ----------------------------------------------------------------------
# --- MEMBER API Routes (Fitness Management, Class Enrollment, Metrics) ---
# ----------------------------------------------------------------------

@app.route('/api/member/<int:member_id>/enroll', methods=['POST'])
@role_required('member')
def api_enroll_in_class(member_id):
    if session.get('user_id') != member_id:
        return jsonify({'message': 'Unauthorized ID for enrollment.'}), 403

    class_id = request.form.get('class_id', type=int)

    if not class_id:
        flash('Invalid Class ID provided.', 'error')
        return redirect(url_for('member_dashboard')) # Or specific class listing page

    success = enroll_in_class(member_id=member_id, class_id=class_id)

    if success:
        flash('Successfully enrolled in the class!', 'success')
    else:
        # Service layer should provide specific error reasons (full, already enrolled)
        flash('Enrollment failed. The class may be full or you are already registered.', 'error')
    
    return redirect(url_for('member_dashboard'))

@app.route('/api/member/<int:member_id>/unenroll/<int:class_id>', methods=['POST'])
@role_required('member')
def api_cancel_enrollment(member_id, class_id):
    if session.get('user_id') != member_id:
        return jsonify({'message': 'Unauthorized ID for enrollment.'}), 403

    success = cancel_class_enrollment(member_id=member_id, class_id=class_id)

    if success:
        flash('Successfully cancelled enrollment.', 'success')
    else:
        flash('Failed to cancel enrollment. Are you sure you were enrolled?', 'error')
    
    return redirect(url_for('member_dashboard'))


@app.route('/api/member/<int:member_id>/log_metric', methods=['POST'])
@role_required('member')
def api_log_metric(member_id):
    if session.get('user_id') != member_id:
        return jsonify({'message': 'Unauthorized ID for logging metrics.'}), 403

    data = request.form
    try:
        weight = float(data.get('weight'))
        height = float(data.get('height'))
        heart_rate = int(data.get('heart_rate'))
        record_date_str = data.get('record_date')
        record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
    except Exception:
        flash('Invalid input for metric logging.', 'error')
        return redirect(url_for('member_dashboard'))

    success = log_health_metric(
        member_id=member_id,
        record_date=record_date,
        weight=weight,
        height=height,
        heart_rate=heart_rate
    )

    if success:
        flash('Health metrics logged successfully.', 'success')
    else:
        flash('Failed to log health metrics.', 'error')
    
    return redirect(url_for('member_dashboard'))


@app.route('/api/member/<int:member_id>/update_goal', methods=['POST'])
@role_required('member')
def api_update_goal(member_id):
    if session.get('user_id') != member_id:
        return jsonify({'message': 'Unauthorized ID for updating goals.'}), 403

    data = request.form
    try:
        target_type = data.get('target_type')
        target_value = float(data.get('target_value'))
        end_date_str = data.get('end_date')
        
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        is_active = data.get('is_active') == 'True'
    except Exception:
        flash('Invalid input for goal update.', 'error')
        return redirect(url_for('member_dashboard'))

    success = update_member_goal(
        member_id=member_id,
        target_type=target_type,
        target_value=target_value,
        end_date=end_date,
        is_active=is_active
    )

    if success:
        flash('Fitness goal updated successfully.', 'success')
    else:
        flash('Failed to update fitness goal.', 'error')
    
    return redirect(url_for('member_dashboard'))


# ----------------------------------------------------------------------
# --- TRAINER API Routes (Schedule Management, Class Roster) ---
# ----------------------------------------------------------------------

# Retaining the previous route and making it role-specific
@app.route('/api/trainer/<int:trainer_id>/availability', methods=['POST'])
@role_required('trainer')
def api_update_availability(trainer_id):
    if session.get('user_id') != trainer_id:
        return jsonify({'message': 'Unauthorized ID for updating availability.'}), 403

    data = request.form
    try:
        day_of_week = data.get('day_of_week')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
    except Exception:
        flash('Invalid input for availability.', 'error')
        return redirect(url_for('trainer_dashboard'))

    success = update_trainer_availability(
        trainer_id=trainer_id,
        day_of_week=day_of_week,
        start_time_str=start_time_str,
        end_time_str=end_time_str
    )

    if success:
        flash("Availability updated successfully.", 'success')
    else:
        flash("Availability update failed.", 'error')
        
    return redirect(url_for('trainer_dashboard'))

@app.route('/api/trainer/<int:trainer_id>/schedule', methods=['GET'])
@role_required('trainer')
def api_view_schedule(trainer_id):
    if session.get('user_id') != trainer_id:
        return jsonify({'message': 'Unauthorized ID.'}), 403
    
    # Example query parameters for date range
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except Exception:
        # Default to a 7-day schedule if dates are not provided or invalid
        end_date = date.today()
        start_date = end_date - datetime.timedelta(days=6)

    schedule_data = view_trainer_schedule(trainer_id=trainer_id, start_date=start_date, end_date=end_date)
    
    # In a real app, this would return JSON to be rendered by JS on the dashboard
    # For simplicity, we just flash a message if there's an error
    if schedule_data is None:
        flash("Could not retrieve schedule.", 'error')
        return redirect(url_for('trainer_dashboard'))
        
    return jsonify(schedule_data) # Send schedule data as JSON


@app.route('/api/trainer/class/<int:class_id>/roster', methods=['GET'])
@role_required('trainer')
def api_view_class_roster(class_id):
    # Security: Trainer should only be able to view roster for classes they teach.
    # The view_class_roster service function should handle this check internally.
    trainer_id = session.get('user_id')
    roster = view_class_roster(class_id=class_id, trainer_id=trainer_id)

    if roster is None:
        flash("You are not authorized to view this class roster or the class does not exist.", 'error')
        return jsonify({'message': 'Unauthorized or not found'}), 404
        
    return jsonify({'class_id': class_id, 'roster': roster})


# ----------------------------------------------------------------------
# --- ADMIN API Routes (Trainer/Class/Equipment/Invoice Management) ---
# ----------------------------------------------------------------------

@app.route('/api/admin/register_trainer', methods=['POST'])
@role_required('admin')
def api_register_trainer():
    data = request.form
    required_fields = ['name', 'email', 'password', 'start_date']
    if not all(field in data for field in required_fields):
        flash('Missing required fields for trainer registration.', 'error')
        return redirect(url_for('admin_dashboard'))

    try:
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
    except Exception:
        flash('Invalid date format.', 'error')
        return redirect(url_for('admin_dashboard'))

    trainer_id = register_trainer(name=name, email=email, password=password, start_date=start_date)

    if trainer_id:
        flash(f'Trainer {name} registered successfully with ID: {trainer_id}.', 'success')
    else:
        flash('Trainer registration failed (e.g., email already exists).', 'error')
    
    return redirect(url_for('admin_dashboard'))


@app.route('/api/admin/create_class', methods=['POST'])
@role_required('admin')
def api_create_class():
    data = request.form
    required_fields = ['class_type', 'trainer_id', 'room_id', 'start_time', 'capacity']
    if not all(field in data for field in required_fields):
        flash('Missing required fields for class creation.', 'error')
        return redirect(url_for('admin_dashboard'))

    try:
        class_type = data.get('class_type')
        trainer_id = int(data.get('trainer_id'))
        room_id = int(data.get('room_id'))
        # Expecting start_time in 'YYYY-MM-DD HH:MM:SS' format (or similar)
        start_time = datetime.strptime(data.get('start_time'), '%Y-%m-%d %H:%M:%S') 
        capacity = int(data.get('capacity'))
    except Exception:
        flash('Invalid input format for class details.', 'error')
        return redirect(url_for('admin_dashboard'))

    class_id = create_class(
        class_type=class_type,
        trainer_id=trainer_id,
        room_id=room_id,
        start_time=start_time,
        capacity=capacity,
        admin_id=session.get('user_id') # Pass the logged-in admin's ID
    )

    if class_id:
        flash(f'Class "{class_type}" created successfully with ID: {class_id}.', 'success')
    else:
        flash('Class creation failed (e.g., trainer/room busy, invalid IDs).', 'error')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/api/admin/remove_class/<int:class_id>', methods=['POST'])
@role_required('admin')
def api_remove_class(class_id):
    success = remove_class(class_id=class_id, admin_id=session.get('user_id'))
    
    if success:
        flash(f'Class ID {class_id} removed successfully.', 'success')
    else:
        flash(f'Failed to remove class ID {class_id}.', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/api/admin/update_invoice/<int:invoice_id>', methods=['POST'])
@role_required('admin')
def api_update_invoice(invoice_id):
    data = request.form
    try:
        total_price = float(data.get('total_price'))
        price_type = data.get('price_type')
        status = data.get('status')
    except Exception:
        flash('Invalid price or status input.', 'error')
        return redirect(url_for('admin_dashboard'))

    success = update_invoice(
        invoice_id=invoice_id,
        total_price=total_price,
        price_type=price_type,
        status=status,
        admin_id=session.get('user_id')
    )

    if success:
        flash(f'Invoice ID {invoice_id} updated successfully.', 'success')
    else:
        flash(f'Failed to update invoice ID {invoice_id}.', 'error')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/api/admin/add_equipment', methods=['POST'])
@role_required('admin')
def api_add_equipment():
    data = request.form
    required_fields = ['equipment_name', 'current_status']
    if not all(field in data for field in required_fields):
        flash('Missing required fields for equipment.', 'error')
        return redirect(url_for('admin_dashboard'))

    equipment_name = data.get('equipment_name')
    current_status = data.get('current_status')
    
    equipment_id = add_equipment(
        equipment_name=equipment_name,
        current_status=current_status,
        admin_id=session.get('user_id')
    )

    if equipment_id:
        flash(f'Equipment "{equipment_name}" added successfully with ID {equipment_id}.', 'success')
    else:
        flash('Failed to add equipment.', 'error')
        
    return redirect(url_for('admin_dashboard'))


@app.route('/api/admin/log_maintenance/<int:equipment_id>', methods=['POST'])
@role_required('admin')
def api_log_maintenance(equipment_id):
    data = request.form
    try:
        issue_description = data.get('issue_description')
        repair_task = data.get('repair_task')
        resolution_date_str = data.get('resolution_date')
        
        resolution_date = datetime.strptime(resolution_date_str, '%Y-%m-%d').date()
    except Exception:
        flash('Invalid input for maintenance log.', 'error')
        return redirect(url_for('admin_dashboard'))

    success = log_equipment_maintenance(
        equipment_id=equipment_id,
        issue_description=issue_description,
        repair_task=repair_task,
        resolution_date=resolution_date,
        admin_id=session.get('user_id')
    )

    if success:
        flash(f'Maintenance logged successfully for equipment {equipment_id}.', 'success')
    else:
        flash(f'Failed to log maintenance for equipment {equipment_id}.', 'error')
        
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    # Initialize the database before running the app
    try:
        initialize() 
    except Exception as e:
        logger.critical(f"Application startup halted due to failed database initialization: {e}", exc_info=True)
        sys.exit(1)
        
    app.run(debug=True)