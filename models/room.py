from sqlalchemy import Column, Integer,String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Room(Base):
    __tablename__ = 'room'

    # Primary Key
    room_id = Column(Integer, primary_key=True, unique=True)
    equipment_id = Column(Integer, ForeignKey('equipment.equipment_id'))
    room_type = Column(String(50), nullable= False)
    capacity = Column(Integer, nullable= False)
    current_status = Column(String(100))
    #class_id = Column(Integer, ForeignKey('Classes.class_id'))
    admin_id = Column(Integer, ForeignKey('admin.admin_id'))

    admin = relationship("Admin", back_populates="room_manage")
    classes = relationship("Classes", back_populates="room")
    def __init__(self, room_id, admin_id, equipment_id, room_type, capacity, current_status):
        self.room_id = room_id
        self.admin_id = admin_id
        self.equipment_id = equipment_id
        self.room_type = room_type
        self.capacity = capacity
        self.current_status = current_status
        