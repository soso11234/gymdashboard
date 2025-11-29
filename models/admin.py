from sqlalchemy import Column, Integer,String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Admin(Base):
    __tablename__ = 'admin'

    # Primary Key
    admin_id = Column(Integer, primary_key=True,unique = True)
    
    #history
    name = Column(String(100), nullable = False)
    email = Column(String(100), nullable = False, unique=True)
    password = Column(String(50), nullable= False)
    #relationships
    equipment_log = relationship("Equipment_log", back_populates="admin")
    equipment = relationship("Equipment", back_populates="admin")
    invoice = relationship("Invoice", back_populates="admin")
    room_manage = relationship("Room", back_populates="admin")
    def __init__(self, admin_id, name, email, password):
        self.admin_id = admin_id
        self.name = name
        self.email = email
        self.password = password