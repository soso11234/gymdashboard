from sqlalchemy import Column, Integer,DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 

# This model is the Supertype for both Admin and Trainer roles.
class class_enrollment(Base):
    __tablename__ = 'class_enrollment'

    # Primary Key
    member_id = Column(Integer, ForeignKey('member.member_id'),nullable = False, primary_key= True)
    class_id = Column(Integer, ForeignKey('classes.class_id'), nullable= False, primary_key= True)
    #history
    enrollment_date = Column(DateTime, nullable= False)


    member = relationship("member", back_populates="class_enrollment")
    classes = relationship("classes", back_populates="class_enrollment")
    def __init__(self, member_id, class_id, enrollment_date):
        self.member_id = member_id
        self.class_id = class_id
        self.enrollment_date = enrollment_date
        