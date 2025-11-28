from sqlalchemy import Column, Integer,String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Equipment(Base):
    __tablename__ = 'equipment'

    # Primary Key
    equipment_id = Column(Integer, primary_key=True,unique = True)
    # member info
    admin_id = Column(Integer, ForeignKey('admin.admin_id'),nullable = False)
    #history
    equipment_name = Column(String(100), nullable = False)
    current_status = Column(String(100), nullable = False)
    #relationships
    admin = relationship("admin", back_populates="equipment")

    def __init__(self, equipment_id, admin_id, equipment_name, current_status):
        self.equipment_id = equipment_id
        self.admin_id = admin_id
        self.equipment_name = equipment_name
        self.current_status = current_status