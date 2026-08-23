from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Gym(Base):
    __tablename__ = "gyms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    owner_name = Column(String(200), nullable=False)
    phone = Column(String(15), nullable=False)
    email = Column(String(200), unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    business_type = Column(String(50), default="gym")
    city = Column(String(100))
    upi_id = Column(String(100), nullable=True)
    # Subscription fields
    subscription_status = Column(String(20), default="trial")   # trial / active / expired
    subscription_start = Column(Date, nullable=True)
    subscription_end = Column(Date, nullable=True)
    subscription_plan = Column(String(50), default="monthly")   # monthly / quarterly / yearly
    created_at = Column(DateTime, default=func.now())

    members = relationship("Member", back_populates="gym")
    leads = relationship("Lead", back_populates="gym")
    payments = relationship("Payment", back_populates="gym")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    full_name = Column(String(200), nullable=False)
    phone = Column(String(15), nullable=False)
    email = Column(String(200))
    membership_type = Column(String(50), default="monthly")
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="members")
    payments = relationship("Payment", back_populates="member")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    name = Column(String(200), nullable=False)
    phone = Column(String(15), nullable=False)
    email = Column(String(200))
    source = Column(String(50), default="website")
    status = Column(String(50), default="booked") # booked, completed, converted
    trial_date = Column(DateTime, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="leads")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    member_id = Column(Integer, ForeignKey("members.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    payment_mode = Column(String(50), default="UPI")
    payment_status = Column(String(50), default="completed")
    payment_date = Column(Date, default=func.current_date())
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="payments")
    member = relationship("Member", back_populates="payments")