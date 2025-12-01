from sqlalchemy import Column, Integer,DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Trainer_availability(Base):
    __tablename__ = 'trainer_availability'

    # Primary Key
    availability_id = Column(Integer, primary_key=True,unique = True)
    # member info
    trainer_id = Column(Integer, ForeignKey('trainer.trainer_id'),nullable = False)

    #history
    start_time = Column(DateTime, nullable= False)
    end_time = Column(DateTime, nullable= False)
    day_of_week = Column(String(50), nullable=False)


    trainer = relationship("Trainer", back_populates="trainer_availability")

    def __init__(self, availability_id, trainer_id, day_of_week, start_time, end_time):
        self.availability_id = availability_id
        self.trainer_id = trainer_id
        self.start_time = start_time
        self.end_time = end_time
        self.day_of_week = day_of_week
    def __repr__(self):
        return f"<trianer_availiabilty (id={self.availability_id}, trainer_id={self.trainer_id}, start time='{self.start_time}, end time='{self.end_time}'>"