from sqlalchemy import Column,Boolean, Integer,String,DateTime,Float, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Fitness_goal(Base):
    __tablename__ = 'fitness_goal'

    # Primary Key
    goal_id = Column(Integer, primary_key=True,unique = True)
    # member info
    member_id = Column(Integer, ForeignKey('member.member_id'),nullable = False)

    #history
    target_type = Column(String(100), nullable= False)
    target_value = Column(Float, nullable=False) 
    start_date = Column(DateTime, nullable= False)
    end_date = Column(DateTime, nullable= False)
    is_active = Column(Boolean, nullable= False)


    member = relationship("Member", back_populates="fitness_goal")

    def __init__(self, member_id, target_type, target_value, start_date, end_date, is_active):
        self.member_id = member_id
        self.target_type = target_type
        self.target_value = target_value
        self.start_date = start_date
        self.end_date = end_date
        self.is_active = is_active
        
    def __repr__(self):
        return f"<fitness goal (id={self.goal_id}, member_id={self.member_id}, target_type='{self.target_type}'>"