from sqlalchemy import Column, Integer,String,DateTime,ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 
from datetime import timedelta
# This model is the Supertype for both Admin and Trainer roles.
class Classes(Base):
    __tablename__ = 'classes'

    # Primary Key
    class_id = Column(Integer, primary_key=True,unique = True)
    # member info
    trainer_id = Column(Integer, ForeignKey('trainer.trainer_id'),nullable = False)
    room_id = Column(Integer, ForeignKey('room.room_id'),nullable = False)
    #history
    class_type = Column(String(100), nullable = False)
    number_members = Column(Integer, nullable = False)
    start_time = Column(DateTime, nullable= False)
    end_time = Column(DateTime, nullable= False)
    #relationships
    trainer = relationship("trainer", back_populates="classes")
    room = relationship("room", back_populates="classes")

    def __init__(self, class_id, trainer_id, room_id, class_type, start_time,number_members):
        self.class_id = class_id
        self.trainer_id = trainer_id
        self.room_id = room_id
        self.class_type = class_type
        self.start_time = start_time
        self.end_time = start_time+ timedelta(minutes=90)
        self.number_members = number_members
    def __repr__(self):
        return f"<classes (id={self.class_id}, trainer_id={self.trainer_id},room_id={self.room_id}, start time='{self.start_time}, end time='{self.end_time}'>"