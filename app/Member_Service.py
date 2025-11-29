from models.base import SessionLocal
from models.member import Member
from models.fitness_goal import Fitness_goal
from models.metric import Metric
from models.class_enrollment import Class_enrollment
from models.classes import Classes
from models.room import Room
# Import the new PersonalTrainingSession model
#from models.personal_training_session import PersonalTrainingSession 
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, or_ # Imported or_ for login check
from sqlalchemy.orm import Session 

# Helper for opening and closing sessions
def _execute_transaction(func):
    """Decorator to handle session management (open, commit, rollback, close).
    The decorated function must accept 'session' as its first argument.
    """
    def wrapper(*args, **kwargs):
        session = SessionLocal()
        # The first argument 'session' is provided by the decorator
        args_with_session = (session,) + args
        try:
            result = func(*args_with_session, **kwargs)
            session.commit()
            return result
        except IntegrityError as e:
            session.rollback()
            print(f"Error: Database constraint violation (e.g., duplicate email). Details: {e}")
            return None
        except Exception as e:
            session.rollback()
            print(f"Error: An unexpected error occurred. Details: {e}")
            return None
        finally:
            session.close()
    return wrapper

# --- Member Management Functions ---

@_execute_transaction
def register_member(name: str, email: str, date_of_birth_str: str, password: str, phone_number: Optional[str] = None, gender: Optional[str] = None) -> Optional[int]:
    """
    Registers a new member, including creating their initial fitness goal and metric entries.
    Returns the new member's ID on success, or None on failure (e.g., duplicate email).
    """
    session = SessionLocal()
    try:
        # 1. Prepare data
        date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d')
        
        # 2. Find the next available ID
        # Get the maximum member_id and add 1, default to 1 if no members exist
        max_id = session.query(func.max(Member.member_id)).scalar()
        new_member_id = (max_id or 0) + 1
        
        # 3. Create Member
        new_member = Member(
            member_id=new_member_id,
            name=name,
            email=email,
            date_of_birth=date_of_birth,
            password=password,
            phone_number=phone_number or "N/A", # Use 'N/A' if phone is None
            gender=gender
        )
        session.add(new_member)
        
        # 4. Create initial Fitness Goal (using placeholder data)
        # Assuming the initial goal description is captured from the registration form
        initial_goal_description = "Establish baseline fitness and understand gym routines."
        
        # Find the next available goal_id
        max_goal_id = session.query(func.max(Fitness_goal.goal_id)).scalar()
        new_goal_id = (max_goal_id or 0) + 1
        
        initial_goal = Fitness_goal(
            goal_id=new_goal_id,
            member_id=new_member_id,
            target_type=initial_goal_description, # Using the description in target_type for now
            target_value=0.0, # Placeholder value
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=90), # 3-month initial goal
            is_active=True
        )
        session.add(initial_goal)
        
        # 5. Commit is handled by the decorator
        print(f"Success: Registered new member ID {new_member_id} and created initial goal.")
        return new_member_id
        
    except IntegrityError:
        # Handled by decorator
        return None
    except Exception as e:
        # Handled by decorator
        print(f"Unexpected error in register_member: {e}")
        return None

# check member password
@_execute_transaction
def check_member(session: Session, email: str, password: str) -> Optional[int]:
    """
    Checks if a member with the given email and password exists.
    Returns the member_id on success, or None on failure.
    """
    # FIX: Use comma-separated expressions instead of Python's 'and' for SQLAlchemy filters.
    member_match = session.query(Member).filter(
        Member.email == email, 
        Member.password == password
    ).first()
    print(Member.email)
    print(Member.password)

    if member_match:
        print(f"Success: Member {member_match.member_id} logged in.")
        return True
    else:
        print("Error: Invalid email or password.")
        return None

# log health metrics
@_execute_transaction
def log_health(session: Session, member_id: int, record_date: str, weight: int, height: int, heart_rate: int) -> bool:
    """
    Logs new health metrics for a member.
    """
    try:
        # 1. Prepare data
        record_dt = datetime.strptime(record_date, '%Y-%m-%d')
        
        # 2. Check if member exists
        if not session.query(Member).filter(Member.member_id == member_id).first():
            print(f"Error: No member id: {member_id} found.")
            return False

        # 3. Find the next available metric_id
        max_id = session.query(func.max(Metric.metric_id)).scalar()
        new_metric_id = (max_id or 0) + 1
        
        # 4. Create Metric
        new_metric = Metric(
            metric_id=new_metric_id,
            member_id=member_id,
            record_date=record_dt,
            weight=weight,
            height=height,
            heart_rate=heart_rate
        )
        session.add(new_metric)
        
        # 5. Commit is handled by the decorator
        print(f"Success: Logged new metric ID {new_metric_id} for member {member_id}.")
        return True
        
    except Exception as e:
        # Handled by decorator
        print(f"Unexpected error in log_health: {e}")
        return False

# update member goal
@_execute_transaction
def update_member_goal(session: Session, goal_id: int, target_type: str, target_value: float, end_date_str: str, is_active: bool) -> bool:
    """
    Updates an existing fitness goal for a member.
    """
    try:
        # 1. Prepare data
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # 2. Retrieve the existing goal
        goal_to_update = session.query(Fitness_goal).filter(
            Fitness_goal.goal_id == goal_id
        ).one_or_none()
        
        if not goal_to_update:
            print(f"Error: Goal with ID {goal_id} not found.")
            return False
            
        # 3. Update the attributes
        goal_to_update.target_type = target_type
        goal_to_update.target_value = target_value
        goal_to_update.end_date = end_date
        goal_to_update.is_active = is_active
        
        # 4. Commit is handled by the decorator
        print(f"Success: Updated goal ID {goal_id}.")
        return True
        
    except Exception as e:
        # Handled by decorator
        print(f"Unexpected error in update_member_goal: {e}")
        return False

# Retrieve dashboard data
@_execute_transaction
def get_member_dashboard_data(session: Session, member_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves all necessary data for the member dashboard.
    """
    try:
        member = session.query(Member).filter(Member.member_id == member_id).first()
        if not member:
            print(f"Error: No member id: {member_id} found.")
            return None

        # Fetch current active goals
        active_goals = session.query(Fitness_goal).filter(
            Fitness_goal.member_id == member_id,
            Fitness_goal.is_active == True
        ).order_by(Fitness_goal.end_date).all()
        
        # Fetch latest metrics (Max 5, ordered by date descending)
        latest_metrics = session.query(Metric).filter(
            Metric.member_id == member_id
        ).order_by(Metric.record_date.desc()).limit(5).all()
        
        # Format output
        goals_data = [{
            'goal_id': g.goal_id,
            'target_type': g.target_type,
            'target_value': g.target_value,
            'start_date': g.start_date.strftime('%Y-%m-%d'),
            'end_date': g.end_date.strftime('%Y-%m-%d'),
            'is_active': g.is_active
        } for g in active_goals]
        
        metrics_data = [{
            'metric_id': m.metric_id,
            'record_date': m.record_date.strftime('%Y-%m-%d'),
            'weight': m.weight,
            'height': m.height,
            'heart_rate': m.heart_rate
        } for m in latest_metrics]
        """
        # Fetch scheduled personal training sessions (upcoming)
        upcoming_pt_sessions = session.query(PersonalTrainingSession).filter(
            PersonalTrainingSession.member_id == member_id,
            PersonalTrainingSession.start_time >= datetime.now()
        ).order_by(PersonalTrainingSession.start_time).all()
        
        pt_data = [{
            'session_id': s.session_id,
            'trainer_id': s.trainer_id,
            'start_time': s.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': s.end_time.strftime('%Y-%m-%d %H:%M')
        } for s in upcoming_pt_sessions]
        """

        # Fetch scheduled group classes (upcoming)
        upcoming_classes = session.query(Classes).join(Class_enrollment).filter(
            Class_enrollment.member_id == member_id,
            Classes.start_time >= datetime.now()
        ).order_by(Classes.start_time).all()

        class_data = [{
            'class_id': c.class_id,
            'class_type': c.class_type,
            'trainer_id': c.trainer_id,
            'start_time': c.start_time.strftime('%Y-%m-%d %H:%M')
        } for c in upcoming_classes]

        return {
            'member_name': member.name,
            'goals': goals_data,
            'metrics': metrics_data,
            'classes': class_data
        }
        
    except Exception as e:
        print(f"Error retrieving member dashboard data for ID {member_id}. Details: {e}")
        return None


# Enroll member in a class
@_execute_transaction
def enroll_in_class(session: Session, member_id: int, class_id: int) -> bool:
    """
    Enrolls a member into a class, checking for capacity and duplicate enrollment.
    """
    member = session.query(Member).filter(Member.member_id == member_id).first()
    class_to_enroll = session.query(Classes).filter(Classes.class_id == class_id).first()
    
    if not member:
        print(f"Error: No member id: {member_id} found.")
        return False
    if not class_to_enroll:
        print(f"Error: No class id: {class_id} found.")
        return False
    
    # 1. Check if member is already enrolled
    if session.query(Class_enrollment).filter(
        Class_enrollment.member_id == member_id, 
        Class_enrollment.class_id == class_id
    ).first():
        print(f"Error: Member ID {member_id} is already registered for class {class_id}.")
        return False

    # 2. Check current enrollment count vs. class capacity
    current_enrollment_count = session.query(func.count(Class_enrollment.member_id)).filter(
        Class_enrollment.class_id == class_id
    ).scalar()
    
    # Assuming the Classes model has a 'capacity' attribute
    class_capacity = class_to_enroll.number_members # Use the number_members attribute as capacity
    
    if current_enrollment_count >= class_capacity:
        print(f"Error: The class {class_id} is already full (Capacity: {class_capacity}, Current: {current_enrollment_count}).")
        return False
        
    # 3. Perform enrollment
    new_enrollment = Class_enrollment(
        member_id=member_id, 
        class_id=class_id, 
        enrollment_date=datetime.now()
    )
    session.add(new_enrollment)
    print(f"Success: Member {member_id} enrolled in class {class_id}.")
    
    return True