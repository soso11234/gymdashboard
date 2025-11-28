from sqlalchemy import Column, Integer, String,DateTime
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Member(Base):
    __tablename__ = 'member'

    # Primary Key
    member_id = Column(Integer, primary_key=True,unique = True)
    # member info
    name = Column(String(100), nullable= False)
    email= Column(String(100), nullable= False, unique= True)
    gender = Column(String(50), nullable= True)
    date_of_birth = Column(DateTime, nullable= False)
    phone_number = Column(String(100), nullable= False)
    #relationship
    metrics = relationship("Metric", back_populates="member", cascade="all,delete-orphan")
    fitness_goals = relationship("Fitness_Goal", back_populates="member", cascade="all,delete-orphan")
    pt_session = relationship("PersonalTrainingSession", back_populates="member", cascade="all,delete-orphan")
    enrollments = relationship("class_enrollment", back_populates="member", cascade="all,delete-orphan")
    invoice = relationship("invoice", back_populates="member", cascade="all,delete-orphan")
        
    def __init__(self, name, email, date_of_birth, phone_number=None, gender= None):
        self.name = name
        self.email = email
        self.date_of_birth = date_of_birth
        self.phone_number = phone_number
        self.gender = gender

    def __repr__(self):
        return f"<Member(id={self.member_id}, name='{self.name}', email='{self.email}')>"