from models.base import SessionLocal
from models.member import Member
from models.fitness_goal import Fitness_Goal
from models.metric import Metric
from models.class_enrollment import class_enrollment
from models.classes import Classes
from models.room import room
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_

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
def register_member(session, contact: str, name: str, email: str, gender: str, date_of_birth: tuple) -> Optional[Member]:
    """Registers a new member."""
    try: 
        # Convert date tuple (year, month, day) to date object
        dob = date(date_of_birth[0], date_of_birth[1], date_of_birth[2])
    except ValueError:
        print("Error: Not a valid date format (expected year, month, day).")
        return None
    
    new_member = Member(
        name=name,
        email=email,
        gender=gender,
        date_of_birth=dob,
        phone_number=contact
    )
    session.add(new_member)
    # The commit is handled by the decorator
    print(f"Success: New Member {name} registered")
    return new_member

@_execute_transaction
def update_member_goal(session, member_id: int, goal_data: Optional[Dict[str, Any]] = None) -> bool:
    """Updates an existing active goal or creates a new one for a member."""
    member = session.query(Member).filter(Member.member_id == member_id).first()
    if not member:
        print(f"Error: No Member ID {member_id} in the database")
        return False
    
    print(f"Updating profile details for member {member_id}.")
    
    if goal_data:
        # NOTE: Corrected typo 'tartget_type' to 'target_type'
        target_type = goal_data.get('target_type') 
        
        existing_goal = session.query(Fitness_Goal).filter(
            Fitness_Goal.member_id == member_id,
            Fitness_Goal.target_type == target_type,
            Fitness_Goal.is_active == True
        ).first() # Corrected .fist() to .first()

        is_active = goal_data.pop('is_active', True)
        
        if existing_goal:
            # Update existing goal
            for key, value in goal_data.items():
                if hasattr(existing_goal, key) and value is not None:
                    setattr(existing_goal, key, value)
            setattr(existing_goal, 'is_active', is_active)
            print(f"Success: Updated existing goal for type '{target_type}'.")
        else:
            # Create a new goal
            # Add member_id and is_active to the goal_data before creation
            goal_data['member_id'] = member_id
            goal_data['is_active'] = is_active
            
            # The start_date should probably be set automatically if not provided, 
            # but we assume it's in goal_data or handled by the model default if applicable.
            
            new_goal = Fitness_Goal(**goal_data)
            session.add(new_goal)
            print(f"Success: Created new fitness goal for type '{target_type}'.")
    return True

# --- Metric Logging Function ---

@_execute_transaction
def log_health(session, member_id: int, weight: float, height: float, heart_rate: int) -> bool:
    """Logs health metrics for a member."""
    # Corrected typo 'wegiht' to 'weight' in function signature and usage
    member = session.query(Member).filter(Member.member_id == member_id).first()
    if not member:
        print(f"Failure: Member ID {member_id} not found.")
        return False
        
    new_metric = Metric(
        member_id=member_id,
        record_date=datetime.now(),
        # Cast to int as per the Metric model definition (assuming it uses Integer)
        weight=int(weight), 
        height=int(height), 
        heart_rate=heart_rate
    )
    session.add(new_metric)
    # The commit is handled by the decorator
    print("Success: New metric added.")
    return True

# --- Dashboard Data Function (Read-Only) ---

@_execute_transaction
def get_member_dashboard_data(session, member_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves dashboard data for a member, including metrics, goals, and upcoming classes."""
    
    member = session.query(Member).filter(Member.member_id == member_id).first()
    if not member:
        return None

    # A. Latest Metric
    latest_metric = session.query(Metric).filter(Metric.member_id == member_id).order_by(Metric.record_date.desc()).first()

    # B. Active Goals (Uses is_active=True from your model)
    active_goals = session.query(Fitness_Goal).filter(
        Fitness_Goal.member_id == member_id,
        Fitness_Goal.is_active == True
    ).all()
    
    # C. Total Metric History Count
    metric_count = session.query(func.count(Metric.metric_id)).filter(Metric.member_id == member_id).scalar()

    # D. Upcoming Classes Count - Corrected query logic using explicit join
    # Query: Count the Classes where the member is enrolled AND the class start time is in the future.
    upcoming_classes_count = session.query(func.count(Classes.class_id)).join(class_enrollment,
        and_(
            class_enrollment.class_id == Classes.class_id,
            class_enrollment.member_id == member_id
        )
    ).filter(
        Classes.start_time > datetime.now()
    ).scalar()

    # E. Assemble Data
    dashboard_data = {
        "member_name": member.name,
        "member_id": member.member_id,
        "latest_metric": {
            "weight": latest_metric.weight,
            "height": latest_metric.height,
            "record_date": latest_metric.record_date.strftime("%Y-%m-%d %H:%M:%S")
        } if latest_metric else "No data",
        "active_goals": [
            {"type": goal.target_type, "target": goal.target_value, "end_date": goal.end_date.strftime("%Y-%m-%d")} 
            for goal in active_goals
        ],
        "total_metrics_logged": metric_count,
        "upcoming_classes_count": upcoming_classes_count
    }

    return dashboard_data

# --- Class Enrollment Function ---

@_execute_transaction
def register_class(session, member_id: int, class_id: int) -> bool:
    """Registers a member for a class, checking capacity and existing enrollment."""
    
    member = session.query(Member).filter(Member.member_id == member_id).first()
    class_to_enroll = session.query(Classes).filter(Classes.class_id == class_id).first() # Corrected variable name
    
    if not member:
        print(f"Error: No member id: {member_id} found.")
        return False
    if not class_to_enroll:
        print(f"Error: No class id: {class_id} found.")
        return False
    
    # 1. Check if member is already enrolled
    if session.query(class_enrollment).filter(
        class_enrollment.member_id == member_id, 
        class_enrollment.class_id == class_id
    ).first():
        print(f"Error: Member ID {member_id} is already registered for class {class_id}.")
        return False

    # 2. Check current enrollment count vs. class capacity
    current_enrollment_count = session.query(func.count(class_enrollment.member_id)).filter(
        class_enrollment.class_id == class_id
    ).scalar()
    
    class_capacity = class_to_enroll.capacity # Use the capacity directly from the Classes object
    
    if current_enrollment_count >= class_capacity:
        print(f"Error: The class {class_id} is already full (Capacity: {class_capacity}, Current: {current_enrollment_count}).")
        return False
        
    # 3. Perform enrollment
    new_enrollment = class_enrollment(
        member_id=member_id,
        class_id=class_id,
        enrollment_date=datetime.now(),
    )
    session.add(new_enrollment)
    # The commit is handled by the decorator
    print(f"Success: Registered member {member_id} to class {class_id}.")
    return True