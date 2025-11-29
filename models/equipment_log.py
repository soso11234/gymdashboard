from sqlalchemy import Column, Integer,String,DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Equipment_log(Base):
    __tablename__ = 'equipment_log'

    # Primary Key
    log_id = Column(Integer, primary_key=True,unique = True)
    # member info
    admin_id = Column(Integer, ForeignKey('admin.admin_id'),nullable = False)
    equipment_id = Column(Integer, ForeignKey('equipment.equipment_id'),nullable= False)
    #history
    issue_description = Column(String(100), nullable = False)
    repair_task = Column(String(100), nullable = False)
    log_date = Column(DateTime)
    resolution_date = Column(DateTime)
    #relationships
    admin = relationship("Admin", back_populates="equipment_log")
    equipment = relationship("Equipment", back_populates="equipment_log")

    def __init__(self, equipment_id, admin_id, repair_task, resolution_date,issue):
        self.equipment_id = equipment_id
        self.admin_id = admin_id
        self.repair_task = repair_task
        self.resolution_date = resolution_date
        self.issue_description = issue