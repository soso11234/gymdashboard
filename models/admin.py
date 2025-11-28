from sqlalchemy import Column, Integer,String
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class admin(Base):
    __tablename__ = 'admin'

    # Primary Key
    admin_id = Column(Integer, primary_key=True,unique = True)
    #history
    name = Column(String(100), nullable = False)
    email = Column(String(100), nullable = False, unique=True)

    #relationships
    equipment_log = relationship("equipment_log", back_populates="admin")
    equipment = relationship("equipment", back_populates="admin")
    invoice = relationship("invoice", back_populates="admin")
    def __init__(self, admin_id, name, email):
        self.admin_id = admin_id
        self.name = name
        self.email = email