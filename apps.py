import os

from flask import Flask, render_template_string, request, redirect, url_for, jsonify

from datetime import datetime, date

from db_init import initialized_db, insert_sample_data # Import database functions

import sys

import logging

from functools import wraps



# Setup logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')



# Adjust Python path to find service files

sys.path.append(os.path.dirname(os.path.abspath(__file__)))



# Import Service functions

from app.Member_Service import register_member, log_health, update_member_goal, get_member_dashboard_data

from app.Admin_Service import register_trainer, update_invoice

from app.Trainer_Service import update_trainer_availability, view_trainer_schedule

from models.base import SessionLocal

from models.trainer import Trainer

from models.room import room

from models.classes import Classes



app = Flask(__name__)



# --- Helper Functions ---



# Simple simulated authentication (Replace with real session management in production)

def get_user_role_id(name):

    """Placeholder for authentication: returns a tuple (user_id, role)."""

    if name.lower() == 'admin':

        return 1, 'admin' # Admin ID 1

    elif name.lower() == 'bob':

        return 101, 'trainer' # Trainer ID 101

    elif name.lower() == 'alice':

        return 201, 'member' # Member ID 201

    return None, 'guest'



def requires_auth(role):

    def decorator(f):

        @wraps(f)

        def decorated_function(*args, **kwargs):

            # In a real app, you would check session cookie/token here.

            # For testing, we use a simple header/query parameter.

            user_id = request.headers.get('X-User-ID') or request.args.get('user_id')

            user_role = request.headers.get('X-User-Role') or request.args.get('user_role')

           

            if not user_id or user_role != role:

                logging.warning(f"Auth failed for role={role}. User ID: {user_id}, Role: {user_role}")

                return "Unauthorized or Invalid Role for this action.", 403

           

            return f(int(user_id), *args, **kwargs)

        return decorated_function

    return decorator



# --- Database Initialization ---





def initialize():

    """Ensure database tables and sample data exist before the first request."""

    # Ensure all tables are created and sample data is inserted for a fresh start.

    initialized_db()

    insert_sample_data()

    logging.info("Database initialized and sample data inserted.")

   

# --- Global Frontend Views (HTML files used as templates) ---



# Read HTML files for serving them as simple Flask templates

def load_html_template(filename):

    try:

        with open(filename, 'r') as f:

            return f.read()

    except FileNotFoundError:

        return f"<h1>Error: Template file '{filename}' not found.</h1>", 404



@app.route('/')

def home():

    """Default route, redirects to registration for ease of testing."""

    return redirect(url_for('show_registration'))



@app.route('/register', methods=['GET'])

def show_registration():

    """Serves the registration page."""

    return load_html_template('registration.html')



@app.route('/member_dashboard', methods=['GET'])

@requires_auth('member')

def member_dashboard(user_id):

    """Serves the member dashboard."""

    # Note: In a real app, data for the dashboard (metrics, goals, classes)

    # would be fetched here using Member_Service functions before rendering the template.

    template_content = load_html_template('member dash.html')

    # Placeholder name replacement for visual check

    return template_content.replace("[Member Name]", f"Member {user_id}")



@app.route('/trainer_dashboard', methods=['GET'])

@requires_auth('trainer')

def trainer_dashboard(user_id):

    """Serves the trainer dashboard."""

    # Note: Fetch schedule data here using Trainer_Service.view_trainer_schedule

    template_content = load_html_template('trainer dash.html')

    return template_content.replace("[Trainer Name]", f"Trainer {user_id}")



@app.route('/admin_dashboard', methods=['GET'])

@requires_auth('admin')

def admin_dashboard(user_id):

    """Serves the admin dashboard."""

    # Note: Fetch necessary data (equipment, rooms, trainers) for forms

    template_content = load_html_template('admin dash.html')

    return template_content



# --- API Endpoints: Connecting Frontend Forms to Backend Services ---



@app.route('/api/register', methods=['POST'])

def api_register():

    """Handles new member registration from the form."""

    try:

        data = request.form

       

        name = data.get('name')

        email = data.get('email')

        dob_str = data.get('dob')

        phone = data.get('phone')

        gender = data.get('gender')

       

        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()



        member_id = register_member(

            name=name,

            email=email,

            date_of_birth=dob,

            phone_number=phone,

            gender=gender

        )



        if member_id:

            # Also register their initial metric (simplified)

            record_metric(

                member_id=member_id,

                record_date=datetime.now(),

                height=int(data.get('height')),

                weight=int(data.get('weight')),

                heart_rate=int(data.get('heart_rate'))

            )

            # Simulate successful login and redirect to dashboard

            return redirect(url_for('member_dashboard', user_id=member_id, user_role='member'))

        else:

            return "Registration failed. Email might be in use or data is invalid.", 400



    except Exception as e:

        logging.error(f"Registration Error: {e}", exc_info=True)

        return f"An internal error occurred during registration: {e}", 500



@app.route('/api/admin/create_class', methods=['POST'])

@requires_auth('admin')

def api_create_class(admin_id):

    """Handles class creation from the Admin Dashboard."""

    try:

        data = request.form

        trainer_id = int(data.get('trainer_id'))

        room_id = int(data.get('room_id'))

        class_type = data.get('class_type')

        capacity = int(data.get('capacity'))

        start_time_str = data.get('start_time')

        end_time_str = data.get('end_time')



        # Combine today's date with time for a full datetime object (simplified for testing)

        today = date.today()

        start_datetime = datetime.combine(today, datetime.strptime(start_time_str, '%H:%M').time())

        end_datetime = datetime.combine(today, datetime.strptime(end_time_str, '%H:%M').time())



        # Call the service function

        class_id = create_class(

            trainer_id=trainer_id,

            room_id=room_id,

            class_type=class_type,

            capacity=capacity,

            start_time=start_datetime,

            end_time=end_datetime

        )

       

        if class_id:

            return redirect(url_for('admin_dashboard', user_id=admin_id, user_role='admin'))

        else:

            return "Class creation failed (e.g., time/room conflict).", 400



    except Exception as e:

        logging.error(f"Class Creation Error: {e}", exc_info=True)

        return f"An internal error occurred during class creation: {e}", 500



@app.route('/api/trainer/availability', methods=['POST'])

@requires_auth('trainer')

def api_update_availability(trainer_id):

    """Handles trainer availability update from the Trainer Dashboard."""

    try:

        data = request.form

        day_of_week = data.get('day_of_week')

        start_time_str = data.get('start_time')

        end_time_str = data.get('end_time')



        # Call the service function

        success = update_trainer_availability(

            trainer_id=trainer_id,

            day_of_week=day_of_week,

            start_time_str=start_time_str,

            end_time_str=end_time_str

        )



        if success:

            return redirect(url_for('trainer_dashboard', user_id=trainer_id, user_role='trainer'))

        else:

            return "Availability update failed (e.g., time overlap).", 400



    except Exception as e:

        logging.error(f"Availability Update Error: {e}", exc_info=True)

        return f"An internal error occurred: {e}", 500





# You would add more API routes for enrollment, equipment update, etc.



if __name__ == '__main__':

    # Initialize the database before running the app

    initialize()

    # Run the Flask app

    # host='0.0.0.0' is important for running in environments like Canvas

    app.run(debug=True, host='0.0.0.0', port=5000)