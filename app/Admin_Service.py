from models.base import SessionLocal
from models.trainer import Trainer
from models.member import Member
from models.classes import Classes
from models.trainer_availability import Trainer_availability
from models.admin import admin
from models.room import room
from models.invoice import invoice
from models.classes import Classes
from models.equipment import Equipment
from models.equipment_log import Equipment_log

from datetime import datetime, date, timedelta
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

#register admin
@_execute_transaction
def register_trainer(session: Session, name: str, email:str) -> Optional[admin]:
    try:
        new_admin = admin(
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
        admin_id = session.query(admin.admin_id).filter(
            admin.name == name
        ).all()
        
        if admin_id is None:
             print(f"Lookup failed: Trainer named '{name}' not found.")
             return None
             
        return admin_id
        
    except Exception as e:
        print(f"ERROR during admin_id: {e}")
        return None

#each trainer's dashboard
@_execute_transaction
def schedule_group_class(class_id: int, trainer_id: int, room_id: int, class_type: str, start_time: datetime.datetime, day_of_week:str) -> bool:
    """Schedules a new group class, checking for room and trainer availability."""
    session = SessionLocal()
    try:
        # Check if Trainer exists
        if not session.query(Trainer).filter(Trainer.trainer_id == trainer_id).first():
            print(f"Error: Trainer ID {trainer_id} does not exist.")
            return False

        # Check if Room exists and get its capacity
        current_room = session.query(room).filter(room.room_id == room_id).first()
        if not current_room:
            print(f"Error: Room ID {room_id} does not exist.")
            return False
        
        # Check tranier & room conflict
        if check_class_conflict(session,room_id, trainer_id, start_time):
            print("There is no conflict")
        else:
            print("Time conflict, try again")
            return False

        # Check for room and trainer conflicts (Simplified check - full conflict logic would be extensive)
        # Note: A full implementation would check for overlapping times with existing classes/sessions.
        new_class = Classes(
            class_id=class_id,
            trainer_id=trainer_id,
            room_id=room_id,
            class_type=class_type,
            number_members=0,
            start_time=start_time,
            end_time=start_time+timedelta(minutes=90)
        )
        session.add(new_class)
        session.commit()
        print(f"Success: Class '{class_type}' scheduled in Room {room_id} from {start_time.strftime('%H:%M')}.")
        return True
    except IntegrityError as e:
        session.rollback()
        print(f"Database Error scheduling class: {e}")
        return False
    finally:
        session.close()

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
    session = get_session()
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
        invoices = session.query(invoice).filter(invoice.member_id == member_id).all()
        
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
        new_invoice = invoice(
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
        if session.query(invoice).filter(invoice.member_id == member_id):
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
        current_invoice = session.query(invoice).filter(
            invoice.invoice_id == invoice_id
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