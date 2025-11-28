from sqlalchemy import Column, Integer,String,DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Trainer(Base):
    __tablename__ = 'trainer'

    # Primary Key
    trainer_id = Column(Integer, primary_key=True,unique = True)

    #history
    name = Column(String(100), nullable= False)
    start_date = Column(DateTime, nullable= False)


    trainer_availability = relationship("trainer_availability", back_populates="trainer")
    personal_training_session = relationship("personal_training_session",back_populates="trainer")
    classes = relationship("classes", back_populates="trainer")

    def __init__(self, trainer_id, name , start_date):
        self.trainer_id = trainer_id
        self.name = name
        self.start_date = start_date
        