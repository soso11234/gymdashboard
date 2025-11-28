from models.base import SessionLocal
from models.trainer import Trainer
from models.classes import Classes
from models.trainer_availability import Trainer_availability
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy import func, and_
from sqlalchemy.orm import Session 

# Helper for opening and closing sessions
def _execute_transaction(func):
    """Decorator to handle session management (open, commit, rollback, close).
    The decorated function must accept 'session' as its first argument.
    """
    def wrapper(*args, **kwargs):
        session = SessionLocal()
        # The first argument 'session' is provided by the decorator
        # We need to prepend the session to the arguments list
        args_with_session = (session,) + args
        try:
            result = func(*args_with_session, **kwargs)
            
            # Commit only for functions that are intended to write data
            write_functions = ['register_trainer', 'update_trainer_availability']
            if func.__name__ in write_functions:
                session.commit()
                print(f"Transaction committed for {func.__name__}.")
                
            return result
        except IntegrityError as e:
            session.rollback()
            print(f"Error: Database constraint violation during {func.__name__}. Details: {e}")
            return None
        except Exception as e:
            session.rollback()
            print(f"Error: An unexpected error occurred during {func.__name__}. Details: {e}")
            return None
        finally:
            session.close()
    return wrapper

#register trainer
@_execute_transaction
def register_trainer(session: Session, name: str) -> Optional[Trainer]:
    new_trainer = Trainer(
        name=name,
        start_date=datetime.now()
    )
    session.add(new_trainer)
    print(f"Success: New Trainer {name} registered.")
    return new_trainer

#get trianer_id
@_execute_transaction
def get_trainer_id(session: Session, name: str) -> Optional[int]:
    try:
        trainer_id = session.query(Trainer.trainer_id).filter(
            Trainer.name == name
        ).all()
        
        if trainer_id is None:
             print(f"Lookup failed: Trainer named '{name}' not found.")
             return None
             
        return trainer_id
        
    except Exception as e:
        print(f"ERROR during get_trainer_id: {e}")
        return None

#each trainer's dashboard
@_execute_transaction
def get_trainer_board(session: Session, trainer_id: int) -> Optional[Dict[str, Any]]:
    trainer = session.query(Trainer).filter(Trainer.trainer_id == trainer_id).first()
    if not trainer:
        print(f"Error: Cannot find trainer ID {trainer_id}")
        return None
        
    # Query classes that are in the future
    upcoming_class = session.query(Classes).filter(
        Classes.trainer_id == trainer_id,
        Classes.start_time > datetime.now()
    ).order_by(Classes.start_time).all()

    dashbord_data = {
        "Trainer name": trainer.name,
        "Upcoming Classes": [
            {
                "Type": c.class_type,
                "Start time": c.start_time.strftime("%m-%d %H:%M"),
                "End time": c.end_time.strftime("%m-%d %H:%M") 
            } for c in upcoming_class
        ]
    }
    return dashbord_data

#check overlap
def check_availability_overlap(session: Session, trainer_id: int, day_of_week: str, start_time_str: str, end_time_str: str) -> bool:
    try:
        regi_start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        regi_end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
    except ValueError:
        print("Error: Invalid time format. Please use 'HH:MM:SS'.")
        return False

    conflict = session.query(Trainer_availability).filter(
        and_(
            Trainer_availability.trainer_id == trainer_id, # CRITICAL FIX: Scope to the trainer
            Trainer_availability.day_of_week == day_of_week,
            regi_start_time < Trainer_availability.end_time,
            regi_end_time > Trainer_availability.start_time
        )
    ).first()
    
    if conflict:
        print(f"Error: Time conflict found on {day_of_week} with existing slot {conflict.start_time.strftime('%H:%M:%S')}-{conflict.end_time.strftime('%H:%M:%S')}")
        return False # Conflict found
    else:
        print("Success: Time slot is available.")
        return True # No conflict

#update trainer availability 
@_execute_transaction
def update_trainer_availability(session: Session, trainer_id: int, day_of_week: str, start_time_str: str, end_time_str: str) -> bool:
    """Adds a new availability slot for a trainer after checking for overlaps."""
    try:
        # Convert string times to time objects
        start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
        end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
    except ValueError:
        print("Error: Invalid time format. Please use 'HH:MM:SS'.")
        return False
        
    trainer = session.query(Trainer).filter(Trainer.trainer_id == trainer_id).first()
    if not trainer:
        print(f"Error: Trainer ID {trainer_id} not found.")
        return False

    if not check_availability_overlap(session, trainer_id, day_of_week, start_time_str, end_time_str):
        print("Error : TIme overlap")
        return False
    else:
        # Create new slot
        new_availability = Trainer_availability(
            trainer_id=trainer_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time
        )
        session.add(new_availability)
        print(f"Success: Added new availability for Trainer {trainer_id} on {day_of_week} from {start_time_str} to {end_time_str}.")
        
    return True


# view full schedule
@_execute_transaction
def view_trainer_schedule(session: Session, trainer_id: int, start_date: date, end_date: date) -> Optional[Dict[str, List[Dict[str, Any]]]]:
    """
    Retrieves the full schedule (Classes and PT Sessions) for a trainer within a date range.
    """
    trainer = session.query(Trainer).filter(Trainer.trainer_id == trainer_id).first()
    if not trainer:
        print(f"Error: Trainer ID {trainer_id} not found.")
        return None

    classes_schedule = session.query(Classes).filter(
        Classes.trainer_id == trainer_id,
        Classes.start_time.between(start_date, end_date + datetime.timedelta(days=1)) # Include end of end_date
    ).order_by(Classes.start_time).all()


    schedule_data = {
        "classes": [
            {
                "type": c.class_type,
                "time": c.start_time.strftime("%Y-%m-%d %H:%M"),
                "duration_minutes": 90,
                "room_id": c.room_id
            } for c in classes_schedule
        ]
    }

    
    return schedule_data