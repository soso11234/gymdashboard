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
def register_member(session:Session, name: str, email: str, gender:str, date_of_birth_str: str, password: str, phone_number:str) -> Optional[int]:
    """
    Registers a new member, including creating their initial fitness goal and metric entries.
    Returns the new member's ID on success, or None on failure (e.g., duplicate email).
    """
    #session = SessionLocal()
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
            phone_number=phone_number,
            gender=gender
        )
        session.add(new_member)
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
def check_member(self, email: str, password: str) -> Optional[int]:
    """
    Checks if a member with the given email and password exists.
    Returns the member_id on success, or None on failure.
    """
    session = SessionLocal()
    member_match = session.query(Member).filter(
        Member.email == email, 
        Member.password == password
    ).first()


    if member_match:
        print(f"Success: Member {member_match.member_id} logged in.")
        return member_match.member_id
    else:
        print("Error: Invalid email or password.")
        return None

# log health metrics
@_execute_transaction
def log_health(member_id: int, weight: int, height: int, heart_rate: int) -> bool:
    """
    Logs new health metrics for a member.
    """
    session = SessionLocal()
    try:
        # 1. Prepare data
        record_dt = datetime.now()
        
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

@_execute_transaction
def get_available_classes(session: Session, member_id: int) -> List[Dict[str, Any]]:
    """
    Fetches all currently available classes, including capacity, current enrollment count, 
    and whether the specified member is already enrolled.
    """
    current_time = datetime.now()
    
    # Subquery 1: Count current enrollments for each class
    enrollment_count = session.query(
        Class_enrollment.class_id, 
        func.count(Class_enrollment.member_id).label('current_enrollment')
    ).group_by(Class_enrollment.class_id).subquery()
    
    # Subquery 2: Check if the current member is enrolled in each class
    member_enrollment = session.query(
        Class_enrollment.class_id
    ).filter(
        Class_enrollment.member_id == member_id
    ).subquery()


    # Query Classes, left-joining with both subqueries
    classes = session.query(
        Classes.class_id,
        Classes.class_type,
        Classes.trainer_id,
        Classes.room_id,
        Classes.start_time,
        Classes.number_members, # This is the capacity
        func.coalesce(enrollment_count.c.current_enrollment, 0).label('current_enrollment'),
        member_enrollment.c.class_id.isnot(None).label('is_enrolled')
    ).outerjoin(enrollment_count, Classes.class_id == enrollment_count.c.class_id
    ).outerjoin(member_enrollment, Classes.class_id == member_enrollment.c.class_id
    ).filter(
        Classes.start_time >= current_time
    ).order_by(Classes.start_time).all()

    classes_data = [{
        "class_id": c.class_id,
        "class_type": c.class_type,
        "trainer_id": c.trainer_id,
        "room_id": c.room_id,
        "start_time": c.start_time.strftime("%Y-%m-%d %H:%M"),
        "number_members": c.number_members, # Capacity
        "current_enrollment": c.current_enrollment,
        "is_enrolled": c.is_enrolled # NEW: Check if the member is already enrolled
    } for c in classes]

    return classes_data

@_execute_transaction
def cancel_member_class_enrollment(session: Session, member_id: int, class_id: int) -> bool:
    """
    Cancels a member's enrollment in a class, ensuring the class is in the future.
    Returns True on successful cancellation, False otherwise.
    """
    try:
        # Check if enrollment exists
        enrollment_to_delete = session.query(Class_enrollment).filter(
            Class_enrollment.member_id == member_id, 
            Class_enrollment.class_id == class_id
        ).one_or_none()
        
        if enrollment_to_delete:
            # Check if the class start time is in the future (cancellation cutoff)
            class_to_check = session.query(Classes).filter(Classes.class_id == class_id).one_or_none()
            
            if not class_to_check:
                print(f"Error: Class ID {class_id} not found for cancellation check.")
                return False

            if class_to_check.start_time <= datetime.now():
                print(f"Error: Cannot cancel enrollment for class {class_id} that has already started.")
                return False
            
            # Perform deletion
            session.delete(enrollment_to_delete)
            print(f"Member ID {member_id} successfully cancelled enrollment in class {class_id}.")
            return True
        else:
            print(f"Error: Enrollment record for Member ID {member_id} in class {class_id} not found.")
            return False
            
    except Exception as e:
        print(f"Error cancelling enrollment for member {member_id} in class {class_id}: {e}")
        return False
    
@_execute_transaction
def set_profile(
    session: Session, 
    member_id: int, 
    name: str, 
    phone_number: Optional[str], 
    gender: Optional[str], 
    new_password: Optional[str] = None
) -> bool:
    try:
        member_match = session.query(Member).filter(
            Member.member_id == member_id
        ).first()
        
        if not member_match:
            print(f"Error: Member ID {member_id} not found for update.")
            return False
        if not phone_number:
            phone_number = member_match.phone_number
        
        if not gender:
            gender = member_match.gender

        # 1. Update basic profile fields
        member_match.name = name
        member_match.phone_number = phone_number
        member_match.gender = gender

        if new_password:
            member_match.password = new_password
            print(f"Member ID {member_id}: Password updated.")
            
        return True
        
    except Exception as e:
        print(f"Error in update_member_profile for member {member_id}: {e}")
        return False
    
@_execute_transaction
def get_profile(session:Session, member_id:int):
    try:
        member_match = session.query(Member).filter(Member.member_id == member_id).one_or_none()
        if member_match:
            return{
                "member_id": member_match.member_id,
                "name": member_match.name,
                "email" : member_match.email,
                "date_of_birth" : member_match.date_of_birth.strftime("%Y-%m-%d") if member_match.date_of_birth else None,
                "Phone number" : member_match.phone_number,
                "Gender" : member_match.gender
            }
        else:
            return None
    except Exception as e:
        print(f"Error : {e}")
    finally:
        session.close()


        

