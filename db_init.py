#import everything about data base.
import os
import sys
from dotenv import load_dotenv
import psycopg2
from datetime import datetime, date, timedelta
from models.base import create_tables
from models.base import SessionLocal
from models.member import Member
from models.admin import Admin
from models.classes import Classes
from models.metric import Metric
from models.invoice import Invoice
from models.trainer import Trainer
from models.room import Room
from models.equipment import Equipment
from models.equipment_log import Equipment_log
from models.class_enrollment import Class_enrollment
from models.fitness_goal import Fitness_goal
from models.invoice import Invoice # 중복 import
from models.trainer_availability import Trainer_availability
#from models.personal_training_session import PersonalTrainingSession 

# Helper to get the database connection from environment variables
def get_db_connection():
    load_dotenv()
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    
    if not all([db_name, db_user, db_pass, db_host, db_port]):
        print("FATAL: Database environment variables are not set.")
        sys.exit(1)
    
    return psycopg2.connect(
        dbname=db_name, 
        user=db_user, 
        password=db_pass, 
        host=db_host, 
        port=db_port
    )

# 1. Create database schema
def initialized_db():
    print("--- Creating database schema ---")
    create_tables()

# 2. Insert sample data
def insert_sample_data():
    session = SessionLocal()
    print("--- Inserting sample data ---")

    try:
        # admin
        admin1 = Admin(admin_id=1, name="Sarah", email="sarah@club.com", password='pass')
        
        # trainer
        trainer1 = Trainer(trainer_id=101, name="Bob",email="bob@club.com", start_date=date(2025,1,2), password='pass')
        trainer2 = Trainer(trainer_id=102, name="Anna",email='anna@club.com', start_date=date(2025,5,9), password='pass')
        
        # member
        member1 = Member(member_id=201, name="Alice", email="alice@club.com", date_of_birth=datetime(2000, 1, 1), 
                          phone_number="555-0101", gender="Female", password='pass')
        member2 = Member(member_id=202, name="Charlie", email="charlie@club.com", date_of_birth=datetime(1995, 5, 20), 
                          phone_number="555-0102", gender="Male", password='pass')
        member3 = Member(member_id=203, name="David", email="david@club.com", date_of_birth=datetime(1988, 11, 15), 
                          phone_number="555-0103", gender="Male", password='pass')
        member4 = Member(member_id=204, name="Eve", email="eve@club.com", date_of_birth=datetime(2002, 3, 10), 
                          phone_number="555-0104", gender="Female", password='pass')

        # equipment
        equipment1 = Equipment(equipment_id=1, admin_id=1, equipment_name="Treadmill A1", current_status="Operational")
        equipment2 = Equipment(equipment_id=2, admin_id=1, equipment_name="Bench Press B3", current_status="Operational")
        equipment3 = Equipment(equipment_id=3, admin_id=1, equipment_name="Yoga Mats (Set)", current_status="Operational")
        equipment4 = Equipment(equipment_id=4, admin_id=1, equipment_name="Spin Bike 10", current_status="Operational")
        equipment5 = Equipment(equipment_id=5, admin_id=1, equipment_name="Dumbbell Rack", current_status="Operational")
        equipment6 = Equipment(equipment_id=6, admin_id=1, equipment_name="Elliptical C2", current_status="Needs Repair")

        # equipment_log (누락되어 있던 데이터 추가 및 올바른 __init__ 인자 사용)
        # __init__(self, equipment_id, admin_id, repair_task, resolution_date, issue):
        log1 = Equipment_log(equipment_id=6, admin_id=1, repair_task="Inspected motor", resolution_date=None, issue="Noise from motor")
        
        # rooms (equipment_type 인자 오류 수정: equipment_id로 통일)
        # room model을 알 수 없어 room1, room2처럼 equipment_id를 사용하는 것으로 통일
        room1 = Room(room_id=1, admin_id=1, equipment_id=1, room_type="Cardio", capacity=30, current_status="Available")
       
        # metrics
        metric1 = Metric(member_id=201, record_date=datetime(2025, 10, 1), weight=65, height=170, heart_rate=70)
        metric2 = Metric(member_id=202, record_date=datetime(2025, 10, 1), weight=85, height=185, heart_rate=65)
        metric3 = Metric(member_id=203, record_date=datetime(2025, 10, 1), weight=75, height=175, heart_rate=72)
        metric4 = Metric(member_id=201, record_date=datetime(2025, 10, 15), weight=64, height=170, heart_rate=68)

        # fitness_goal
        goal1 = Fitness_goal(member_id=201, target_type="Weight Loss", target_value=60.0, start_date=datetime(2025, 10, 1), end_date=datetime(2025, 12, 31), is_active=True)
        goal2 = Fitness_goal(member_id=202, target_type="Muscle Gain", target_value=90.0, start_date=datetime(2025, 10, 1), end_date=datetime(2026, 3, 1), is_active=True)
        goal3 = Fitness_goal(member_id=203, target_type="Endurance", target_value=5.0, start_date=datetime(2025, 11, 1), end_date=datetime(2025, 12, 31), is_active=True)
        
        # classes (capacity 인자 제거)
        start_time_class1 = datetime(2026, 11, 28, 18, 0, 0)
        start_time_class2 = datetime(2026, 11, 29, 10, 0, 0)
        class1 = Classes(class_id=1, trainer_id=101, room_id=1, class_type="Zumba Dance", start_time=start_time_class1, number_members=30)
        class2 = Classes(class_id=2, trainer_id=102, room_id=1, class_type="Power Lifting", start_time=start_time_class2, number_members=25)

        # invoice (due_date 인자 추가)
        issue_date_inv1 = datetime.now()
        invoice1 = Invoice(invoice_id=1, member_id=201, admin_id=1, payment_method="Credit Card", 
                            total_price=50.00, issue_date=issue_date_inv1, due_date=issue_date_inv1 + timedelta(days=14), status="Paid", price_type="Monthly Membership")
        
        issue_date_inv2 = datetime.now() - timedelta(days=5) # 5일 전 발행 가정
        invoice2 = Invoice(invoice_id=2, member_id=202, admin_id=1, payment_method="Debit", 
                            total_price=75.00, issue_date=issue_date_inv2, due_date=issue_date_inv2 + timedelta(days=10), status="Pending", price_type="Personal Training")

        # class_enrollment
        enrollment1 = Class_enrollment(member_id=201, class_id=1, enrollment_date=datetime.now())
        enrollment2 = Class_enrollment(member_id=202, class_id=2, enrollment_date=datetime.now())


        session.add_all([admin1, trainer1, trainer2, member1, member2, member3, member4, 
                         room1, 
                         equipment1, equipment2, equipment3, equipment4, equipment5, equipment6, 
                         log1, # Equipment_log 추가
                         metric1, metric2, metric3, metric4, goal1, goal2, goal3, 
                         class1, class2, invoice1, invoice2, enrollment1, enrollment2])
        session.commit()
        print("   - Sample data inserted successfully.")
    except Exception as e:
        session.rollback()
        # IMPORTANT: Print the full error here to aid debugging the data insertion failure
        print(f"FATAL ERROR inserting sample data: {e}") 
    finally:
        session.close()

# 3. Insert advanced SQL features (Views, Triggers, Indexes)
def insert_advanced_sql_features():
    print("--- Inserting Advanced SQL Features (Views/Triggers) ---")
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Create View V_ClassSummary (DQL Feature)
        VIEW_SQL = """
        CREATE OR REPLACE VIEW V_ClassSummary AS
        SELECT 
            c.class_id,
            c.class_type,
            t.name AS trainer_name,
            c.start_time,
            c.number_members,
            COUNT(ce.member_id) AS current_enrollment
        FROM classes c
        JOIN trainer t ON c.trainer_id = t.trainer_id
        LEFT JOIN class_enrollment ce ON c.class_id = ce.class_id
        GROUP BY c.class_id, c.class_type, t.name, c.start_time, c.number_members
        ORDER BY c.start_time;
        """
        cur.execute(VIEW_SQL)
        print("   - View V_ClassSummary created/updated (DQL Feature).")

        # create index
        cur.execute("CREATE INDEX IF NOT EXISTS idx_member_email ON member (email);")
        print("   - Index idx_member_email created.")


        # trigger - update equipment automatically
        TRIGGER_FUNCTION_SQL = """
        CREATE OR REPLACE FUNCTION update_equipment_status()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Logic: When a new issue is logged, automatically mark the equipment as 'Needs Repair'.
            UPDATE equipment
            SET current_status = 'Needs Repair'
            WHERE equipment_id = NEW.equipment_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        cur.execute(TRIGGER_FUNCTION_SQL)
        
        TRIGGER_SQL = """
        CREATE OR REPLACE TRIGGER trg_equipment_issue
        AFTER INSERT ON equipment_log
        FOR EACH ROW
        EXECUTE FUNCTION update_equipment_status();
        """
        cur.execute(TRIGGER_SQL)
        print("   - Trigger trg_equipment_issue created (Trigger Feature).")
        
        conn.commit()
        cur.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"FATAL ERROR inserting advanced SQL features: {e}")
        # Note: No rollback needed here if the transaction failed.

# Main initialization function called by apps.py
def initialize():
    initialized_db() 
    insert_sample_data()
    insert_advanced_sql_features()
    print("--- Database initialization complete ---")

if __name__ == "__main__":
    initialize()