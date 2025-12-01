from models.base import SessionLocal
from models.trainer import Trainer
from models.member import Member
from models.classes import Classes
from models.trainer_availability import Trainer_availability
from models.admin import Admin
from models.room import Room
from models.invoice import Invoice
from models.equipment import Equipment
from models.equipment_log import Equipment_log

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy import func, and_
from sqlalchemy.orm import Session, joinedload

# Helper for opening and closing sessions
def _execute_transaction(func):
    """Decorator to handle session management (open, commit, rollback, close).
    The decorated function must accept 'session' as its first argument.
    
    FIXED: The commit logic now checks the function name more broadly to ensure
    all write operations (add, update, delete, register, log) are committed.
    """
    def wrapper(*args, **kwargs):
        session = SessionLocal()
        # The first argument 'session' is provided by the decorator
        args_with_session = (session,) + args
        try:
            result = func(*args_with_session, **kwargs)
            
            # Commit only for functions that are intended to write data
            # Check if the function name indicates a modification (add, update, delete, register, log)
            is_write_operation = (
                func.__name__.startswith('add_') or 
                func.__name__.startswith('update_') or 
                func.__name__.startswith('delete_') or 
                func.__name__.startswith('register_') or 
                func.__name__.startswith('log_')
            )
            
            # Add explicit function names if they don't follow the convention but perform a write
            specific_write_functions = ['update_invoice'] 

            if is_write_operation or func.__name__ in specific_write_functions:
                session.commit()
                print(f"Transaction committed for {func.__name__}.")
                
            return result
        except IntegrityError as e:
            session.rollback()
            print(f"Error: Database constraint violation during {func.__name__}. Details: {e}")
            return None
        except NoResultFound as e:
            session.rollback()
            print(f"Error: No result found during {func.__name__}. Details: {e}")
            return None
        except Exception as e:
            session.rollback()
            print(f"An unexpected error occurred during {func.__name__}: {e}")
            return None # Return None on general failure for decorated functions
        finally:
            session.close()

    return wrapper

#find biggest class_id
@_execute_transaction
def get_class_id(session: Session)->int:
    max_id = session.query(func.max(Classes.class_id)).scalar()
    if max_id == 0:
        target_id = 0
    else:
        target_id = max_id +1
    print(f"THIS IS TARGET ID : {target_id}")
    return target_id

#find working trainer
@_execute_transaction
def get_available_trainers_for_timeslot(session: Session, date_str: str, start_time_str: str, end_time_str: str) -> List[dict]:

    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    try:
        # Combine date and time strings
        start_dt_str = f"{date_str} {start_time_str}"
        end_dt_str = f"{date_str} {end_time_str}"
        
        # Convert the combined strings to datetime objects for comparison with Classes.start_time/end_time
        query_start_dt = datetime.strptime(start_dt_str, TIME_FORMAT)
        query_end_dt = datetime.strptime(end_dt_str, TIME_FORMAT)
        
    except ValueError as e:
        print(f"Error parsing date/time strings (Expected Format: YYYY-MM-DD HH:MM:SS): {e}")
        return []

    # 2. Find Trainers who ARE BUSY (Conflict Check)
    # The condition for overlap (BUSY) is:
    # (Existing_Class_Start < Requested_End) AND (Existing_Class_End > Requested_Start)
    busy_trainer_ids_query = session.query(Classes.trainer_id)\
        .filter(and_(
            Classes.start_time < query_end_dt,
            Classes.end_time > query_start_dt
        ))\
        .distinct()\
        .subquery() # Use subquery to select from later

    # 3. Find All Trainers who are NOT in the busy list (AVAILABLE)
    available_trainers = session.query(Trainer)\
        .filter(Trainer.trainer_id.notin_(busy_trainer_ids_query))\
        .all()
        
    # 4. Format and Return the result
    result = []
    for trainer in available_trainers:
        result.append({
            'trainer_id': trainer.trainer_id,
            'name': trainer.name
        })
    
    return result
#register admin
@_execute_transaction
def register_trainer(session: Session, name: str, email:str) -> Optional[Admin]:
    try:
        new_admin = Admin(
            name= name,
            email=email
        )
        session.add(new_admin)
        print(f"Success : register new admin : {name}")
        return new_admin
    except Exception as e:
        print(f"Error : {e}")
        return False

#get trianer_id
@_execute_transaction
def get_admin_id(session: Session, name: str) -> Optional[int]:
    try:
        admin_id = session.query(Admin.admin_id).filter(
            Admin.name == name
        ).all()
        
        if admin_id is None:
             print(f"Lookup failed: Trainer named '{name}' not found.")
             return None
             
        return admin_id
        
    except Exception as e:
        print(f"ERROR during admin_id: {e}")
        return None

@_execute_transaction
def schedule_new_class(
    session: Session, 
    trainer_id: int, 
    room_id: int, 
    class_type: str, 
    start_time: datetime,
) -> bool:
    """Schedules a new class, checking for trainer and room conflicts."""
    
    # Calculate duration (90 minutes) and end_time
    class_duration = timedelta(minutes=90)
    end_time = start_time + class_duration
    other_id = get_class_id()
    print(f"THIS IS CLASS ID = {start_time}")
    
    # Check Trainer and Room availability (Conflict Checking Logic)
    # FIX 2: Conflict checks now use the correctly calculated end_time
    trainer_busy = session.query(Classes).filter(
        Classes.trainer_id == trainer_id,
        Classes.start_time < end_time, # Check if new class ends after a current class starts
        Classes.end_time > start_time  # Check if new class starts before a current class ends
    ).first()
    
    room_busy = session.query(Classes).filter(
        Classes.room_id == room_id,
        Classes.start_time < end_time,
        Classes.end_time > start_time
    ).first()

    if trainer_busy:
        print(f"Conflict: Trainer ID {trainer_id} is busy at this time.")
        return False
    
    if room_busy:
        print(f"Conflict: Room ID {room_id} is busy at this time.")
        return False
        
    try:
        # Create the new Classes object. 
        new_class = Classes(
            class_id=other_id,
            trainer_id=trainer_id,
            room_id=room_id,
            class_type=class_type,
            start_time=start_time,
            number_members=0 
        )
        
        session.add(new_class)
        session.commit()

        print(f"Success: Class ID {other_id} ({class_type}) scheduled.")
        return True
        
    except IntegrityError:
        session.rollback()
        print(f"Integrity Error: Could not create class ID {other_id}.")
        return False
    except Exception as e:
        session.rollback()
        print(f"Unexpected error during class scheduling in service layer: {e}")
        return False


#check overlap
@_execute_transaction
def check_class_conflict(session: Session, room_id: int, trainer_id: int, start_time: datetime) -> bool:
    # 1. Check for Room Conflict (Overlapping Time in the Same Room)
    end_time = start_time + timedelta(minutes= 90)
    room_conflict = session.query(Classes).filter(
        and_(
            Classes.room_id == room_id,
            Classes.start_time < end_time,  
            Classes.end_time > start_time    
        )
    ).first()

    if room_conflict:
        print(f"Conflict: Room {room_id} is already booked by Class ID {room_conflict.class_id} "
              f"from {room_conflict.start_time} to {room_conflict.end_time}.")
        return False

    # 2. Check for Trainer Conflict (Overlapping Time for the Same Trainer)
    trainer_conflict = session.query(Classes).filter(
        and_(
            Classes.trainer_id == trainer_id,
            Classes.start_time < end_time,
            Classes.end_time > start_time
        )
    ).first()

    if trainer_conflict:
        print(f"Conflict: Trainer ID {trainer_id} is already assigned to Class ID {trainer_conflict.class_id} "
              f"from {trainer_conflict.start_time} to {trainer_conflict.end_time}.")
        return False
    else:
        print("Success: Room and Trainer are available for the requested time slot.")
        return True
    
def log_equipment_issue(admin_id: int, equipment_id: int, issue_description: str, repair_task: str) -> bool:
    """
    Logs a maintenance issue for a piece of equipment.
    This action should trigger the database trigger defined in db_init.py 
    to automatically update the equipment status to 'Needs Repair'.
    """
    session = SessionLocal()
    try:
        # Check if Equipment exists
        if not session.query(Equipment).filter(Equipment.equipment_id == equipment_id).first():
            print(f"Error: Equipment ID {equipment_id} does not exist.")
            return False
            
        new_log = Equipment_log(
            admin_id=admin_id,
            equipment_id=equipment_id,
            issue_description=issue_description,
            repair_task=repair_task,
            log_date=datetime.datetime.now(),
            # Resolution date will be NULL until repair is complete
            resolution_date=None
        )
        session.add(new_log)
        session.commit()
        print(f"Success: Issue logged for Equipment ID {equipment_id}. Status should now be 'Needs Repair'.")
        return True
    except IntegrityError as e:
        session.rollback()
        print(f"Database Error logging equipment issue: {e}")
        return False
    finally:
        session.close()

#view invoice
def view_member_invoices(member_id: int):
    """Retrieves all invoices for a specific member."""
    session = SessionLocal()
    try:
        invoices = session.query(Invoice).filter(Invoice.member_id == member_id).all()
        
        if not invoices:
            print(f"No invoices found for Member ID {member_id}.")
            return []

        print(f"\n--- Invoices for Member ID {member_id} ---")
        invoice_list = []
        for inv in invoices:
            data = {
                'ID': inv.invoice_id,
                'Total': f"${inv.total_price:.2f}",
                'Status': inv.status,
                'Issue Date': inv.issue_date.strftime('%Y-%m-%d') if inv.issue_date else 'N/A',
                'Due Date': inv.due_date.strftime('%Y-%m-%d') if inv.due_date else 'N/A',
                'Payment Method': inv.payment_method
            }
            invoice_list.append(data)
            print(f"  ID: {data['ID']} | Total: {data['Total']} | Status: {data['Status']} | Due: {data['Due Date']}")
        
        return invoice_list
    finally:
        session.close()

#make invoice
def make_invoice(admin_id:int, member_id:int, total_price:int, payment_method:str, status:str, price_type:str) ->bool:
    session = SessionLocal()
    try:
        if(session.query(Member).filter(Member.member_id == member_id)):
            print(f"Find the {member_id}")
        else:
            print(f"Error : not able to find {member_id}")
            return False
        new_invoice = Invoice(
            member_id=member_id,
            admin_id=admin_id,
            total_price=total_price,
            issue_date=datetime.now(),
            payment_method=payment_method,
            status=status,
            price_type=price_type
        )
        session.add(new_invoice)
        print(f"Success : create the invoice of {member_id}")
        return True
    
    except Exception as e:
        print("Error : {e}")
        return False
#get invoice
def get_invoice(member_id:int)->bool:
    session = SessionLocal()
    try:
        if session.query(Invoice).filter(Invoice.member_id == member_id):
            print(f"Find the {member_id}")
            return True
        else:
            print(f"Can not find the {member_id}")
            return False
    except Exception as e:
        print(f"Error : {e}")

#update invoice
@_execute_transaction
def update_invoice(session: Session, invoice_id: int, total_price: float, price_type: str, status: str, admin_id: int) -> bool:
    try:
        current_invoice = session.query(Invoice).filter(
            Invoice.invoice_id == invoice_id
        ).one_or_none()
        
        if not current_invoice:
            print(f"Error: Invoice with ID {invoice_id} not found.")
            return False
            
        # 2. Modify the attributes of the loaded object
        current_invoice.total_price = total_price
        current_invoice.price_type = price_type
        current_invoice.status = status
        current_invoice.admin_id = admin_id  # Optionally update the admin ID who last modified it

        # 3. Commit is handled by the decorator (@_execute_transaction)
        print(f"Success: Invoice ID {invoice_id} for Member {current_invoice.member_id} updated. "
              f"New Price: {total_price}, Status: {status}, Type: {price_type}")
        return True
        
    except Exception:
        # Error logging and rollback are handled by the decorator
        return False
    
def check_admin(email: str, password: str) -> Optional[int]:
    """
    Checks if a member with the given email and password exists.
    Returns the member_id on success, or None on failure.
    """
    session = SessionLocal()
    admin_match = session.query(Admin).filter(
        Admin.email == email, 
        Admin.password == password
    ).first()

    if admin_match:
        print(f"Success: Member {admin_match.admin_id} logged in.")
        return admin_match.admin_id
    else:
        print("Error: Invalid email or password.")
        return None

@_execute_transaction
def get_admin_dashboard_data(session: Session, admin_id: int) -> Dict[str, Any]:
    
    # 1. Calculate time range for the next 7 days
    now = datetime.now()
    one_week_later = now + timedelta(days=7)
    
    # 2. Fetch upcoming classes (joining with Trainer and Room)
    try:
        # --- MODIFICATION: Explicitly select columns instead of the entire Classes object ---
        upcoming_classes = session.query(
            Classes.class_id,
            Classes.class_type,
            Classes.start_time,
            Classes.end_time,
            Classes.number_members,
            Trainer.name.label('trainer_name'),
            Room.room_type.label('room_type'),
            Room.capacity.label('room_capacity')
        ).join(Trainer, Classes.trainer_id == Trainer.trainer_id)\
         .join(Room, Classes.room_id == Room.room_id)\
         .filter(Classes.start_time >= now)\
         .filter(Classes.start_time <= one_week_later)\
         .order_by(Classes.start_time)\
         .limit(5)\
         .all()
        # ----------------------------------------------------------------------------------
         
        # Format the results into a list of dictionaries for Flask rendering
        classes_data = []
        for class_record in upcoming_classes:
            # When explicitly selecting columns, the results are tuples, not mapped objects.
            # We access columns by index or attribute name if using labels.
            classes_data.append({
                'class_id': class_record.class_id,
                'class_type': class_record.class_type,
                'start_time': class_record.start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': class_record.end_time.strftime('%H:%M'),
                'trainer_name': class_record.trainer_name,
                'current_members': class_record.number_members, # This is capacity, based on schedule_new_class logic
                'room_type': class_record.room_type,
                'room_capacity': class_record.room_capacity,
                'capacity_remaining': class_record.room_capacity - class_record.number_members
            })

    except Exception as e:
        print(f"An unexpected error occurred during get_admin_dashboard_data: {e}")
        # Return empty data structure on error
        return {'classes': [], 'trainers': [], 'rooms': []}


    # 3. Fetch list of all trainers
    trainers = session.query(Trainer).order_by(Trainer.trainer_id).all()
    trainers_data = [{'trainer_id': t.trainer_id, 'name': t.name} for t in trainers]

    # 4. Fetch list of all rooms
    rooms = session.query(Room).order_by(Room.room_id).all()
    rooms_data = [{'room_id': r.room_id, 'room_type': r.room_type, 'capacity': r.capacity} for r in rooms]

    return {
        'classes': classes_data,
        'trainers': trainers_data,
        'rooms': rooms_data
    }


@_execute_transaction
def get_next_room_id(session: Session) -> int:
    """Helper to determine the next available room_id."""
    max_id = session.query(func.max(Room.room_id)).scalar()
    return (max_id or 0) + 1

@_execute_transaction
def add_room(session: Session, room_type: str, capacity: int, current_status: str, admin_id: int, equipment_id: Optional[int] = None) -> Optional[int]:
    """
    Adds a new room to the database.
    Fixes the 'unexpected keyword argument room_type' error by including 'room_type' in the signature.
    """
    try:
        new_room_id = get_next_room_id(session) # Get the next ID before creating the object
        
        new_room = Room(
            room_id=new_room_id,
            admin_id=admin_id,
            equipment_id=equipment_id,
            room_type=room_type,
            capacity=capacity,
            current_status=current_status
        )
        session.add(new_room)
        print(f"Success: Room {room_type} (ID: {new_room_id}) added by Admin {admin_id}.")
        # Commit handled by decorator, but explicit log here
        return new_room_id
    except IntegrityError as e:
        # Error logging and rollback are handled by decorator, but explicit log here
        print(f"Integrity Error adding room: {e}")
        return None

def get_all_rooms() -> List[Dict[str, Any]]:
    """Retrieves a list of all rooms. Does not need _execute_transaction as it's a read."""
    session = SessionLocal()
    try:
        rooms = session.query(Room).all()
        rooms_data = [{
            "room_id": r.room_id,
            "name": r.room_type, # Using room_type as the display name
            "capacity": r.capacity,
            "status": r.current_status, # Using current_status as the display status
            "admin_id": r.admin_id,
            "equipment_id": r.equipment_id
        } for r in rooms]
        print(f"Successfully retrieved {len(rooms_data)} rooms.")
        return rooms_data
    except Exception as e:
        print(f"Error retrieving all rooms: {e}")
        return []
    finally:
        session.close()

@_execute_transaction
def get_all_trainers(session: Session) -> List[Dict[str, Any]]:
    """Fetches all trainers with their ID and Name."""
    try:
        # Fetching trainer_id and name
        trainers = session.query(Trainer).all()
        return [{
            'trainer_id': t.trainer_id, 
            'name': t.name
        } for t in trainers]
    except Exception as e:
        print(f"Error fetching all trainers: {e}")
        return []

@_execute_transaction
def get_all_classes(session: Session) -> List[Classes]:
    try:
        classes = session.query(Classes).options(
            joinedload(Classes.room),
            joinedload(Classes.trainer) 
        ).all()
        
        # This loop forces the data to be loaded before the session closes
        for c in classes:
            if c.room:
                _ = c.room.capacity 
            if c.trainer:
                _ = c.trainer.name 
                
        return classes
        
    except Exception as e:
        print(f"Error fetching all classes: {e}")
        return []

@_execute_transaction
def update_room(session: Session, room_id: int, name: str, capacity: int, status: str, admin_id: int) -> bool:
    """Updates an existing room's details."""
    try:
        # Note: The 'name' parameter seems to map to 'room_type' in the Room model based on other code logic. Let's use room_type here for consistency with the model.
        room = session.query(Room).filter(Room.room_id == room_id).one_or_none()
        if not room:
            print(f"Error: Room ID {room_id} not found for update.")
            return False

        room.room_type = name # Assuming 'name' from the flask route maps to 'room_type' in the model
        room.capacity = capacity
        room.current_status = status # Assuming 'status' from the flask route maps to 'current_status' in the model
        room.admin_id = admin_id # Record which admin updated it
        print(f"Success: Room ID {room_id} updated by Admin {admin_id}.")
        return True
    except Exception as e:
        print(f"Error updating room {room_id}: {e}")
        return False

@_execute_transaction
def delete_room(session: Session, room_id: int) -> bool:
    """Deletes a room by its ID."""
    try:
        # Note: A real application should check for active classes using this room first.
        room = session.query(Room).filter(Room.room_id == room_id).one_or_none()
        if not room:
            print(f"Error: Room ID {room_id} not found for deletion.")
            return False
        
        session.delete(room)
        print(f"Success: Room ID {room_id} deleted.")
        return True
    except Exception as e:
        print(f"Error deleting room {room_id}: {e}")
        return False
    
def _check_for_conflict(session, class_id: int, trainer_id: int, room_id: int, start_time: datetime, end_time: datetime) -> Optional[str]:
    """
    Checks for scheduling conflicts with the proposed class time, excluding the class being updated.
    """
    
    # Base filter to exclude the class being updated, and check the time window
    base_filter = [
        Classes.class_id != class_id, 
        Classes.start_time < end_time,
        Classes.end_time > start_time
    ]

    # 1. Trainer Conflict Check
    trainer_filter = base_filter + [Classes.trainer_id == trainer_id]
    trainer_conflict = session.query(Classes).filter(and_(*trainer_filter)).first()

    if trainer_conflict:
        return f"Trainer ID {trainer_id} is busy during the requested time slot."

    # 2. Room Conflict Check
    room_filter = base_filter + [Classes.room_id == room_id]
    room_conflict = session.query(Classes).filter(and_(*room_filter)).first()

    if room_conflict:
        return f"Room ID {room_id} is occupied during the requested time slot."

    return None # No conflict found

#modify class info
@_execute_transaction
def update_class(
    session: Session, 
    class_id: int, 
    class_type: Optional[str] = None,
    start_time: Optional[datetime] = None, # Full datetime object
    trainer_id: Optional[int] = None,
    room_id: Optional[int] = None
) -> str:
    """Updates an existing class's details after performing conflict checks."""
    try:
        class_to_update = session.query(Classes).filter(Classes.class_id == class_id).one_or_none()
        
        if not class_to_update:
            return f"Error: Class ID {class_id} not found."

        # --- Determine Effective Values for Conflict Check ---
        
        # Use new values if provided, otherwise use current values
        effective_start_time = start_time if start_time is not None else class_to_update.start_time
        effective_trainer_id = trainer_id if trainer_id is not None else class_to_update.trainer_id
        effective_room_id = room_id if room_id is not None else class_to_update.room_id

        # Class duration is 90 minutes (based on Classes.__init__)
        effective_end_time = effective_start_time + timedelta(minutes=90)

        # --- 1. Perform Conflict Check ---
        conflict_message = _check_for_conflict(
            session=session,
            class_id=class_id,
            trainer_id=effective_trainer_id,
            room_id=effective_room_id,
            start_time=effective_start_time,
            end_time=effective_end_time
        )
        
        if conflict_message:
            return f"Update failed: {conflict_message}"

        # --- 2. Apply Updates to the Class Object ---
        
        # Update class type (if provided and not empty)
        if class_type is not None and class_type.strip():
            class_to_update.class_type = class_type
            
        # Update trainer/room IDs (if provided)
        if trainer_id is not None:
            class_to_update.trainer_id = trainer_id
            
        if room_id is not None:
            class_to_update.room_id = room_id

        # Update time/date fields (if start_time was provided)
        if start_time is not None:
            class_to_update.start_time = effective_start_time
            class_to_update.end_time = effective_end_time
            class_to_update.start_date = effective_start_time.date() # Update the separate date column

        # The decorator handles session.commit()
        return "Class updated successfully!"

    except IntegrityError:
        return "Update failed: The specified Trainer or Room ID does not exist."
    except Exception as e:
        print(f"Error updating class {class_id}: {e}")
        return f"An unexpected error occurred during update: {e}"
    
@_execute_transaction
def delete_class(session: Session, class_id: int) -> str:
    """
    Deletes a class by its ID, first checking for active member enrollments.
    """
    try:
        # --- 1. Safety Check: Check for enrollments ---
        # Assuming 'Class_enrollment' model is imported and used for tracking members in a class
        try:
            from models.class_enrollment import Class_enrollment
            enrollments_count = session.query(Class_enrollment).filter(
                Class_enrollment.class_id == class_id
            ).count()

            if enrollments_count > 0:
                # Prevent deletion if members are enrolled
                return f"Error: Cannot delete Class ID {class_id} because {enrollments_count} member(s) are still enrolled. Please cancel enrollments first."
        except ImportError:
            # Skip check if the enrollment model isn't available, but log a warning.
            print("WARNING: Class_enrollment model not found. Skipping enrollment check.")


        # --- 2. Find and delete the class ---
        class_to_delete = session.query(Classes).filter(Classes.class_id == class_id).one_or_none()
        
        if not class_to_delete:
            return f"Error: Class ID {class_id} not found for deletion."
        
        session.delete(class_to_delete)
        
        # The decorator handles session.commit()
        return f"Class ID {class_id} deleted successfully."
        
    except IntegrityError:
        # Catches unexpected Foreign Key issues if the enrollment check was incomplete
        return "Deletion failed due to a database integrity error (e.g., related records still exist unexpectedly)."
    except Exception as e:
        print(f"Error deleting class {class_id}: {e}")
        return f"An unexpected error occurred during deletion: {e}"