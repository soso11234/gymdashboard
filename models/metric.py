from sqlalchemy import Column, Integer,DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class Metric(Base):
    __tablename__ = 'metrics'

    # Primary Key
    metric_id = Column(Integer, primary_key=True,unique = True)
    # member info
    member_id = Column(Integer, ForeignKey('member.member_id'),nullable = False)

    #history
    record_date = Column(DateTime, nullable= False)
    height = Column(Integer, nullable= False)
    weight = Column(Integer, nullable= False)
    heart_rate = Column(Integer, nullable= False)

    member = relationship("member", back_populates="metrics")

    def __init__(self, member_id, record_date, weight, height, heart_rate):
        self.member_id = member_id
        self.record_date = record_date
        self.weight = weight
        self.heart_rate = heart_rate
        self.height = height
        
    def __repr__(self):
        return f"<Metric(id={self.metric_id}, member_id={self.member_id}, date='{self.record_date.strftime('%Y-%m-%d')}', weight={self.weight})>"