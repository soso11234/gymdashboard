import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, date
import sys
import logging
from functools import wraps
#from app.Member_Service import register_member, get_member_dashboard_data
from app.Admin_Service import check_admin
from app.Trainer_Service import check_trainer

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
    from app.Member_Service import register_member,set_profile,cancel_member_class_enrollment,log_health, get_profile, check_member, update_member_goal,get_member_dashboard_data,get_available_classes,enroll_in_class
    # Admin Service Imports
    from app.Admin_Service import update_room, delete_class, update_class, get_all_classes, get_all_trainers, get_class_id, get_all_rooms,get_admin_dashboard_data, register_trainer, update_invoice, schedule_new_class, make_invoice, view_member_invoices, delete_room, update_room, add_room
    # Trainer Service Imports
    from app.Trainer_Service import update_trainer_availability, view_trainer_schedule, get_trainer_board
except ImportError as e:
    logger.error(f"FATAL: Failed to import service module. Check file names and function definitions: {e}")
    # Define placeholder functions to avoid application crash during startup
    #def register_member(*args, **kwargs): return None
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

    member_id = check_member(email,password)
    admin_id = check_admin(email,password)
    trainer_id = check_trainer(email, password)
    if member_id:
        session['user_id'] = member_id
        session['user_role'] = 'member'
        return redirect(url_for('member_dashboard'))
    elif admin_id:
        session['user_id'] = admin_id
        session['user_role'] = 'admin'
        return redirect(url_for('admin_dashboard'))
    elif trainer_id:
        session['user_id'] = trainer_id
        session['user_role'] = 'trainer'
        return redirect(url_for('trainer_dashboard'))
    else:
        print("ERORRRRRRRR")
    flash('Invalid email or password.', 'error')
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

@app.route('/schedule/all', methods=['GET'])
@role_required('member')
def show_class_schedule():
    """Displays the list of all available classes for enrollment."""
    member_id = session.get('user_id') # Get member ID
    
    # Fetch all available classes, checking for current member's enrollment status
    available_classes = get_available_classes(member_id=member_id) 

    # Pass the list of classes to the class_schedule.html template (renamed from class_register.html)
    return render_template(
        'class_register.html', 
        classes=available_classes,
        user_role='member'
    )


@app.route('/api/class/register', methods=['POST'])
@role_required('member')
def api_register_class():
    """Handles the form submission to enroll a member in a class."""
    member_id = session['user_id']
    class_id = request.form.get('class_id', type=int)

    if not class_id:
        flash('Invalid class selected.', 'error')
        return redirect(url_for('show_class_schedule'))

    success = enroll_in_class(member_id=member_id, class_id=class_id)
    
    if success:
        flash('Successfully registered for the class!', 'success')
    else:
        # The service function handles specific error messages (like full or already enrolled)
        flash('Failed to register for the class. It might be full, you are already enrolled, or the class time has passed.', 'error')
        
    return redirect(url_for('show_class_schedule'))

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
        new_num = register_member(name,email,gender,dob_str,password,phone)
        print(new_num)
        if not new_num:
            flash('Register failed (email may exist)','error')
            return redirect(url_for('show_registration'))
        try:
            height = float(data.get('height'))
            weight = float(data.get('weight'))
            heart_rate = int(data.get('heart_rate'))
            if log_health(new_num,weight,height,heart_rate):
                print("Sucess register health info")
            else:
                print("Error to register health info")
        except ValueError:
            flash('Invalid format for height, weight, or heart rate. Health metrics not logged.', 'warning')
            # Execution continues past this block

        # --- MISSING RETURN STATEMENT ADDED HERE ---
        # If execution reaches this point, registration was successful.
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('show_login'))
        # -------------------------------------------
        
    except Exception as e:
        logger.error(f"Member Registration Error: {e}", exc_info=True)
        flash(f'An internal error occurred during registration. Please try again.', 'error')
        return redirect(url_for('show_registration'))

@app.route('/api/class/cancel', methods=['POST'])
@role_required('member')
def api_cancel_enrollment():
    """Handles the form submission to cancel a member's enrollment in a class."""
    member_id = session.get('user_id')
    class_id = request.form.get('class_id', type=int) # Class ID is passed via hidden input

    if not class_id:
        flash('Invalid class selected for cancellation.', 'error')
        return redirect(url_for('show_class_schedule'))

    success = cancel_member_class_enrollment(member_id=member_id, class_id=class_id)
    
    if success:
        flash('Successfully cancelled your class enrollment.', 'success')
    else:
        # The service function handles specific error messages (like already started or not enrolled)
        flash('Failed to cancel enrollment. You might not be registered or the class has already started.', 'error')
        
    return redirect(url_for('show_class_schedule'))

# --- Dashboard Routes ---

@app.route('/dashboard/member', methods=['GET'])
@role_required('member')
def member_dashboard():
    member_id = session.get('user_id')
    
    # 1. Call the service function to fetch data
    dashboard_data = get_member_dashboard_data(member_id=member_id)

    if not dashboard_data:
        flash("Could not retrieve dashboard data.", 'error')
        # Redirect to login if data fetch fails, or show a simpler error page
        return redirect(url_for('show_login')) 

    # 2. Pass the retrieved data to the template
    return render_template(
        'member dash.html', 
        user_id=member_id, 
        user_role='member',
        data=dashboard_data)

@app.route('/profile/edit', methods=['GET'])
@role_required('member')
def show_edit_profile():
    """Displays the member profile editing form pre-filled with current data."""
    member_id = session.get('user_id')
    profile_data = get_profile(member_id=member_id)
    
    if not profile_data:
        flash("Could not load profile data.", 'error')
        return redirect(url_for('member_dashboard'))
        
    return render_template(
        'edit_member_profile.html', 
        profile=profile_data
    )

@app.route('/dashboard/trainer', methods=['GET'])
@role_required('trainer')
def trainer_dashboard():
    trainer_id = session.get('user_id')
     # 1. Call the service function to fetch data
    dashboard_data = get_trainer_board(trainer_id=trainer_id)

    if not dashboard_data:
        flash("Could not retrieve dashboard data.", 'error')
        # Redirect to login if data fetch fails, or show a simpler error page
        return redirect(url_for('show_login')) 

    # 2. Pass the retrieved data to the template
    return render_template(
        'trainer dash.html', 
        user_id=trainer_id, 
        user_role='trainer',
        data=dashboard_data)


@app.route('/dashboard/admin', methods=['GET'])
@role_required('admin')
def admin_dashboard():
    admin_id = session.get('user_id')
    # 1. Call the service function to fetch data
    dashboard_data = get_admin_dashboard_data(admin_id=admin_id)
    trainers = get_all_trainers()
    rooms = get_all_rooms()
    if not dashboard_data:
        flash("Could not retrieve dashboard data.", 'error')
        # Redirect to login if data fetch fails, or show a simpler error page
        return redirect(url_for('show_login')) 

    # 2. Pass the retrieved data to the template
    return render_template(
        'admin dash.html', 
        user_id=admin_id,
        user_role='admin',
        all_trainers = trainers,
        all_rooms = rooms,
        data=dashboard_data)


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

@app.route('/api/profile/update', methods=['POST'])
@role_required('member')
def api_update_profile():
    """Handles submission of the member profile update form."""
    member_id = session.get('user_id')
    data = request.form
    
    try:
        success = set_profile(
            member_id=member_id,
            name=data.get('name'),
            phone_number=data.get('phone_number'),
            gender=data.get('gender'),
            new_password=data.get('password') if data.get('password') else None # Only pass password if non-empty
        )
        
        if success:
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('member_dashboard'))
        else:
            flash('Profile update failed. Please check your inputs.', 'error')
            return redirect(url_for('show_edit_profile'))
            
    except Exception as e:
        logger.error(f"Error during profile update: {e}")
        flash('An unexpected error occurred during profile update.', 'error')
        return redirect(url_for('show_edit_profile'))


# ----------------------------------------------------------------------
# --- TRAINER API Routes (Schedule Management, Class Roster) ---
# ----------------------------------------------------------------------


@app.route('/api/trainer/<int:trainer_id>/availability', methods=['POST'])
@role_required('trainer')
def api_update_availability(trainer_id):
    if session.get('user_id') != trainer_id:
        flash('Unauthorized to update this trainer\'s availability.', 'error')
        return redirect(url_for('trainer_dashboard'))

    data = request.form
    try:
        day_of_week = data.get('date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        flash(day_of_week,'success')
        flash(start_time_str,'success')
        flash(end_time_str,'success')

        # Check for missing data
        if not all([day_of_week, start_time_str, end_time_str]):
             # Updated the error message to be slightly more actionable
             flash('Please ensure you have selected the Day, Start Time, and End Time for your availability slot.', 'error')
             return redirect(url_for('trainer_dashboard'))

        # Call the service function, passing arguments by keyword for clarity
        success = update_trainer_availability(
            trainer_id=trainer_id,
            day_of_week=day_of_week,
            start_time_str=start_time_str,
            end_time_str=end_time_str
        )

        if success:
            flash("Availability updated successfully.", 'success')
        else:
            flash("Availability update failed. Please check time format (e.g., '10:00:00') or if the new slot overlaps with an existing one.", 'error')

    except Exception as e:
        logger.error(f"Error processing availability update form: {e}")
        flash('An unexpected error occurred while processing your request.', 'error')
        
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
    required_fields = ['class_type', 'trainer_id', 'room_id', 'start_date', 'start_time']
    
    # 1. Validation Check (Ensures keys exist and values are non-empty strings)
    if not all(data.get(field) and str(data.get(field)).strip() for field in required_fields):
        flash('Missing required fields for class creation. Please fill all fields.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # 2. Retrieve Admin ID from session
    admin_id = session.get('user_id')
    if not admin_id:
        flash('Admin ID not found in session. Please log in again.', 'error')
        return redirect(url_for('login'))
    start_date_str = data.get('start_date')
    start_time_str = data.get('start_time')
    combined_datetime_str = f"{start_date_str} {start_time_str}"
    start_time = datetime.strptime(combined_datetime_str, '%Y-%m-%d %H:%M')
        
    try:
        # Retrieve and process form data
        class_type = data.get('class_type').strip()
        trainer_id = int(data.get('trainer_id'))
        room_id = int(data.get('room_id'))

        
        # The number of registered members starts at 0, as requested
        initial_registered_members = 0 
        
    except ValueError as e:
        print(f"Error converting form data to integer/datetime: {e}")
        flash('Invalid format for ID or Date/Time fields.', 'error')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        print(f"Unexpected error: {e}")
        flash('An unexpected error occurred during data processing.', 'error')
        return redirect(url_for('admin_dashboard'))

    # 3. Call the service function
    success = schedule_new_class(
        trainer_id=trainer_id,
        room_id=room_id,
        class_type=class_type,
        start_time=start_time)
    
    if success:
        flash(f'Class "{class_type}" scheduled successfully.', 'success')
    else:
        # This usually means a conflict (trainer/room busy) or a database error
        flash('Class creation failed. Check for scheduling conflicts with the trainer or room.', 'error')
        
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
@app.route('/admin/manage_classes', methods=['GET'])
@role_required('admin')
def admin_manage_classes():
    try:
        # 1. Fetch all necessary data using the service layer functions
        all_classes = get_all_classes()
        all_trainers = get_all_trainers()
        all_rooms = get_all_rooms()
        
        # 2. Render the HTML template, passing the fetched data
        return render_template(
            'modify class.html',
            all_classes=all_classes,
            all_trainers=all_trainers,
            all_rooms=all_rooms,

        )
    except Exception as e:
        logger.error(f"Error loading class management page: {e}")
        print(f"THE REASON OF ERROR : {e}")
        flash("Failed to load class management data.", "error")
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

@app.route('/admin/manage_rooms')
@role_required('admin')
def manage_rooms():
    """Renders the room management page with a list of all rooms."""
    rooms = get_all_rooms()
    # Note: rooms is expected to be a list of Room objects or dicts for the template
    return render_template('manage room.html', rooms=rooms)

@app.route('/api/admin/add_room', methods=['POST'])
@role_required('admin')
def api_admin_add_room():
    """API endpoint to add a new room."""
    data = request.form
    admin_id = session.get('user_id')
    
    # Using 'room_type' and 'current_status' to match the database model (room.py)
    try:
        room_type = data.get('room_type') 
        capacity = int(data.get('capacity'))
        current_status = data.get('current_status')
        
        if not room_type or capacity is None or capacity < 0 or not current_status:
            flash('Invalid input for adding a room.', 'error')
            return redirect(url_for('manage_rooms'))

        room_id = add_room(
            room_type=room_type,
            capacity=capacity,
            current_status=current_status,
            admin_id=admin_id
        )

        if room_id:
            flash(f'Room {room_type} (ID: {room_id}) added successfully.', 'success')
        else:
            flash(room_id)
            flash('Failed to add room. Check logs for database errors.', 'error')
            
    except Exception as e:
        logger.error(f"An unexpected error occurred during add_room: {e}")
        flash(f'An unexpected error occurred during add_room: {e}', 'error') 
        
    return redirect(url_for('manage_rooms'))


@app.route('/api/admin/update_room/<int:room_id>', methods=['POST'])
@role_required('admin')
def api_update_room(room_id):
    """API endpoint to update an existing room's details."""
    data = request.form
    try:
        name = data.get('room_name')
        capacity = int(data.get('capacity'))
        status = data.get('status')
        admin_id = session.get('user_id')
        
        success = update_room(
            room_id=room_id, 
            name=name, 
            capacity=capacity, 
            status=status, 
            admin_id=admin_id
        )

        if success:
            flash(f'Room ID {room_id} updated successfully.', 'success')
        else:
            flash(f'Failed to update room ID {room_id}. Room not found or update error.', 'error')
            
    except Exception as e:
        logger.error(f"Error in api_update_room: {e}")
        flash('Invalid input or a database error occurred when updating the room.', 'error')
        
    return redirect(url_for('manage_rooms'))

@app.route('/api/admin/delete_room/<int:room_id>', methods=['POST'])
@role_required('admin')
def api_delete_room(room_id):
    """API endpoint to delete a room."""
    
    success = delete_room(room_id=room_id)

    if success:
        flash(f'Room ID {room_id} deleted successfully.', 'success')
    else:
        # NOTE: A real application would check for active classes in this room first.
        flash(f'Failed to delete room ID {room_id}. It might not exist or is in use.', 'error')
        
    return redirect(url_for('manage_rooms'))


@app.route('/api/admin/create_class', methods=['POST'])
@role_required('admin')
def api_add_class():
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
        start_time_str = data.get('start_time')
        start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        start_date = start_time.date()
        
        # --- FIX 1: Generate class_id and day_of_week ---
        # Get the next available class ID (imported from Admin_Service)
        new_class_id = get_class_id() # Assuming this function returns the new unique ID
        
        # Calculate the day of the week string (e.g., 'Monday')
        day_of_week = start_time.strftime('%A')
        # ------------------------------------------------
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error parsing class creation form: {e}")
        flash('Invalid input format for class details.', 'error')
        return redirect(url_for('admin_dashboard'))

    # --- FIX 2: Call the correct function with correct arguments ---
    success = schedule_new_class(
        class_id=new_class_id,        # Now included
        trainer_id=trainer_id,
        room_id=room_id,
        class_type=class_type,
        start_time=start_time,
        day_of_week=start_date        # Now included
        # capacity is not used by schedule_new_class in Admin_Service.py
        # admin_id is not used by schedule_new_class in Admin_Service.py
    )
    # -------------------------------------------------------------
    
    if success:
        flash(f'Class "{class_type}" created successfully with ID: {new_class_id}.', 'success')
    else:
        # schedule_new_class returns False on conflict (e.g., trainer/room busy)
        flash('Class creation failed (e.g., trainer/room busy, invalid IDs).', 'error')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/api/admin/update_class', methods=['POST'])
@role_required('admin')
def api_update_class(): 
    """Handles the form submission from the 'Apply Updates' button."""
    data = request.form
    
    # 1. Get required class ID
    try:
        class_id = int(data.get('class_id'))
    except (TypeError, ValueError):
        flash('Invalid Class ID. Please select a class from the table first.', 'error')
        return redirect(url_for('admin_manage_classes'))

    # 2. Get optional updates (Trainer/Room IDs are handled as strings from the form)
    class_type = data.get('class_type')
    trainer_id_str = data.get('trainer_id')
    room_id_str = data.get('room_id')
    
    # 3. Parse Trainer and Room IDs to int (only if a selection was made)
    # The 'No Change' option should result in a blank string, leading to None here.
    trainer_id = int(trainer_id_str) if trainer_id_str and trainer_id_str.isdigit() else None
    room_id = int(room_id_str) if room_id_str and room_id_str.isdigit() else None
    
    # 4. Parse Date and Time together
    start_time = None
    start_date_str = data.get('start_date')
    start_time_str = data.get('start_time')
    
    if start_date_str and start_time_str:
        try:
            # Combines date and time string: e.g., '2025-12-15 15:00'
            combined_datetime_str = f"{start_date_str} {start_time_str}"
            start_time = datetime.strptime(combined_datetime_str, '%Y-%m-%d %H:%M')
        except ValueError:
            flash('Invalid date or time format provided.', 'error')
            return redirect(url_for('admin_manage_classes'))

    # 5. Call the Service Function to update the class
    result_message = update_class(
        class_id=class_id,
        class_type=class_type,
        start_time=start_time, # Will be None if not updated
        trainer_id=trainer_id, # Will be None if 'No Change' was selected
        room_id=room_id        # Will be None if 'No Change' was selected
    )
    
    # 6. Flash result and redirect
    if "successfully" in result_message:
        flash(result_message, 'success')
    else:
        flash(result_message, 'error')

    return redirect(url_for('admin_manage_classes'))

@app.route('/api/admin/delete_class', methods=['POST'])
@role_required('admin')
def api_delete_class():
    """Handles the form submission from the 'Delete Class' button."""
    class_id_str = request.form.get('class_id')
    
    # 1. Validate Class ID
    try:
        class_id = int(class_id_str)
    except (TypeError, ValueError):
        flash('Invalid Class ID provided for deletion.', 'error')
        return redirect(url_for('admin_manage_classes'))

    # 2. Call the Service Function to delete the class
    result_message = delete_class(class_id=class_id)
    
    # 3. Flash result and redirect
    if "successfully" in result_message:
        flash(result_message, 'success')
    else:
        # This will display the enrollment check error or the general DB error
        flash(result_message, 'error') 

    return redirect(url_for('admin_manage_classes'))

if __name__ == '__main__':
    # Initialize the database before running the app
    try:
        initialize() 
    except Exception as e:
        logger.critical(f"Application startup halted due to failed database initialization: {e}", exc_info=True)
        sys.exit(1)
        
    app.run(debug=True)
