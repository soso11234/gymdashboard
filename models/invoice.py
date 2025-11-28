from sqlalchemy import Column, Integer,String,DateTime,Float, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base 
from datetime import timedelta

# This model is the Supertype for both Admin and Trainer roles.
class invoice(Base):
    __tablename__ = 'invoice'

    # Primary Key
    invoice_id = Column(Integer, primary_key=True,unique = True)
    #foreing key
    member_id = Column(Integer, ForeignKey("member.member_id"))
    admin_id = Column(Integer, ForeignKey("admin.admin_id"))
    #history
    payment_method = Column(String(100), nullable = False)
    status = Column(String(100), nullable = False)
    price_type = Column(String(100), nullable=False)
    total_price = Column(Float)
    issue_date = (DateTime)
    due_date = issue_date + timedelta(days=14)


    #relationships
    member = relationship("member", back_populates="invoice")
    admin = relationship("admin", back_populates="invoice")

    def __init__(self,invoice_id,member_id, admin_id, payment_method, total_price, issue_date, status, price_type):
        self.invoice_id = invoice_id
        self.member_id = member_id
        self.admin_id = admin_id
        self.total_price = total_price
        self.issue_date = issue_date
        self.payment_method = payment_method
        self.status = status
        self.price_type = price_type