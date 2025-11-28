#import everything about data base.
import os
import sys
from dotenv import load_dotenv
import psycopg2
from datetime import datetime, date, timedelta
from models.base import create_tables
from models.base import SessionLocal
from models.member import Member
from models.admin import admin
from models.classes import Classes
from models.metric import Metric
from models.invoice import invoice
from models.trainer import Trainer
from models.room import room
from models.equipment import Equipment
from models.equipment_log import Equipment_log
from models.class_enrollment import class_enrollment
from models.fitness_goal import Fitness_Goal
from models.invoice import invoice
from models.trainer_availability import Trainer_availability

#1. initialized SQL 
def initialized_db():
    print("Create database")
    create_tables()

#2. Insert sameple data
def insert_sample_data():
    session = SessionLocal()
    print("Insert sample data")

    try:
        #admin
        admin1 = admin(admin_id=1, name="Sarah", email="sarah@club.com")
        #trainer
        trainer1 = Trainer(trainer_id=101, name="Bob", start_date=(2025,1,2))
        trainer2 = Trainer(trainer_id=102, name="Anna", start_date=(2025,5,9))
        #member
        member1 = Member(member_id=201,name="Alice", email="alice@club.com",gender="Female",date_of_birth=(1990,1,15))
        member2 = Member(member_id=202,name="Tom", email="tom@club.com",gender="Male",date_of_birth=(2005,11,20))

        session.add_all([admin1,trainer1,trainer2,member1,member2])

        #classes
        class1 = Classes(class_id=101,trainer_id=101,room_id=101,class_type="Yoga",start_time=(2025,11,20,12,00),end_time=(2025,11,20,14,00))
        class2 = Classes(class_id=102,trainer_id=102,room_id=102,class_type="Crossfit",start_time=(2025,11,21,11,00),end_time=(2025,11,21,13,00))
        #room
        room1 = room(room_id= 101, equipment_id=101, room_type="Studio", capacity= 10, current_status="Booking")
        room2 = room(room_id= 102, equipment_id=102, room_type="Crossfit", capacity= 20, current_status="Booking")
        #enrollment
        enrollment1 = class_enrollment(member_id=201, class_id=101, enrollment_date=(2025,11,11))
        enrollment2 = class_enrollment(member_id=202, class_id=102, enrollment_date=(2025,11,10))
        #metrics
        metrics1 = Metric(member_id=201,record_date=(2025,11,11),weight=52, height=168, heart_rate= 120)
        metrics2 = Metric(member_id=202,record_date=(2025,11,11),weight=82, height=183, heart_rate= 110)
        #goals
        goal1 = Fitness_Goal(member_id=201, target_type="being healthy", target_value="0", start_date=(2025,11,11), end_date=(2025,12,11), is_active="Y")
        goal2 = Fitness_Goal(member_id=202, target_type="Like workout", target_value="0", start_date=(2025,11,9),end_date=(2025,12,9),is_active="Y")
        #invoice
        invoice1 = invoice(invoice_id=301,member_id=101, admin_id=201, payment_method="Card", total_price=30, status="Paid", price_type="subscribe")
        invoice2 = invoice(invoice_id=302,member_id=102, admin_id=201, payment_method="Card", total_price=30, status="Paid", price_type="subscribe")
        #equipment_log
        log1 = Equipment_log(log_id=901, equipment_id=401, admin_id=1, issue_description="Belt slipping, requires maintenance.", repair_task="Scheduled for Inspection", log_date=datetime.now())
        session.add_all([class1,class2,room1,room2,enrollment1,enrollment2,metrics1,metrics2,goal1,goal2,invoice1,invoice2,log1])
        session.commit()
        print("sample data insert successfully ! ")


    except Exception as e:
        session.rollback()
        print(f"Error : {e}")
    finally:
        session.close()

#3. view index and trigger
def advanced_sql():
    load_dotenv()

    try:
        conn = psycopg2.connect (
            host=os.getenv("DB_HOST"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
        cur = conn.cursor()
        print("Create Advanced SQL features")
        # View class summary 
        VIEW_SQL = """
        CREATE OR REPLACE VIEW V_ClassSummary AS
        SELECT
            c.class_id,
            c.class_type,
            t.name AS trainer_name,
            c.start_time,
            c.capacity,
            -- Calculate currently enrolled count
            COUNT(ce.member_id) AS currently_enrolled
        FROM classes c
        JOIN trainer t ON c.trainer_id = t.trainer_id
        LEFT JOIN class_enrollment ce ON c.class_id = ce.class_id
        GROUP BY c.class_id, c.class_type, t.name, c.start_time, c.capacity
        ORDER BY c.start_time;
        """
        cur.execute(VIEW_SQL)
        print("   - View V_ClassSummary created/updated (DQL Feature).")

        # create index
        cur.execute("CREATE INDEX idx_member_email ON member (email);")

        #trigger - update equipment automattically
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
        conn.commit()
        cur.close()
        conn.close()
    except SystemError as e:
        print(f"ERROR : {e}")

def main():
    initialized_db()
    insert_sample_data()
    advanced_sql()

if __name__ == "__main__":
    main()