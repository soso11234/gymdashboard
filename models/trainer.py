from sqlalchemy import Column, Integer,String,DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Trainer(Base):
    __tablename__ = 'trainer'

    # Primary Key
    trainer_id = Column(Integer, primary_key=True,unique = True)
    #class_id = Column(Integer, ForeignKey('classes.class_id'))

    #history
    name = Column(String(100), nullable= False)
    email = Column(String(100), nullable= False)
    start_date = Column(DateTime, nullable= False)
    password = Column(String(50), nullable=False)


    trainer_availability = relationship("Trainer_availability", back_populates="trainer")
    #personalTrainingSession = relationship("PersonalTrainingSession",back_populates="trainer")
    classes = relationship("Classes", back_populates="trainer")

    def __init__(self, trainer_id,email, name , start_date,password):
        self.trainer_id = trainer_id
        self.email = email
        self.name = name
        self.start_date = start_date
        self.password = password
        