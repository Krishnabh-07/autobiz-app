import os
import sys

# Ensure backend directory is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, ForeignKey, Text, Numeric, Float
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
    subscription_status = Column(String(20), default="trial")   # trial / active / expired / awaiting_payment
    subscription_plan = Column(String(20), default="monthly")
    subscription_start = Column(Date, nullable=True)
    subscription_end = Column(Date, nullable=True)
    # Payment-at-registration tracking
    selected_plan = Column(String(20), default="monthly")       # monthly / quarterly / yearly
    payment_status = Column(String(20), default="pending")      # pending / verified / rejected
    payment_amount = Column(Numeric(10, 2), nullable=True)
    payment_mode = Column(String(50), default="UPI")
    payment_utr = Column(String(100), nullable=True)
    payment_date = Column(Date, nullable=True)
    transaction_id = Column(String(100), nullable=True)
    owner_email = Column(String(200), index=True, nullable=True)
    is_main_branch = Column(Boolean, default=True)
    parent_id = Column(Integer, ForeignKey("gyms.id"), nullable=True)
    address_line = Column(String(300), nullable=True)
    state = Column(String(100), default="Assam")
    district = Column(String(100), default="Kamrup Metropolitan")
    pincode = Column(String(10), nullable=True)
    village_or_town = Column(String(150), nullable=True)
    autopilot_enabled = Column(Boolean, default=True)
    doctor_specialization = Column(String(150), nullable=True)
    slot_duration_mins = Column(Integer, default=15)
    consultation_fee = Column(Numeric(10, 2), default=500.00)
    working_days = Column(String(100), default="Mon-Sat")
    start_time = Column(String(20), nullable=True)
    end_time = Column(String(20), nullable=True)
    second_start_time = Column(String(20), nullable=True)
    second_end_time = Column(String(20), nullable=True)
    is_onboarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    members = relationship("Member", back_populates="gym", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="gym", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="gym", cascade="all, delete-orphan")
    staff = relationship("Staff", back_populates="gym", cascade="all, delete-orphan")
    attendance = relationship("Attendance", back_populates="gym", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="gym", cascade="all, delete-orphan")
    plans = relationship("ServicePlan", back_populates="gym", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="gym", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="gym", cascade="all, delete-orphan")
    booking_slots = relationship("BookingSlot", back_populates="gym", cascade="all, delete-orphan")
    documents = relationship("DocumentRecord", back_populates="gym", cascade="all, delete-orphan")
    timeline_events = relationship("CustomerTimelineEvent", back_populates="gym", cascade="all, delete-orphan")


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
    attendance = relationship("Attendance", back_populates="member")
    invoices = relationship("Invoice", back_populates="member")


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
    time_slot = Column(String(50), nullable=True) # e.g. "07:00 AM - 08:00 AM"
    lead_score = Column(Integer, default=70) # 0-100 score
    ai_segment = Column(String(20), default="WARM") # HOT, WARM, COLD
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


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    full_name = Column(String(200), nullable=False)
    phone = Column(String(15), nullable=False)
    email = Column(String(200))
    role = Column(String(50), default="trainer") # owner, manager, receptionist, trainer
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="staff")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    member_id = Column(Integer, ForeignKey("members.id"))
    check_in_time = Column(DateTime, default=func.now())
    method = Column(String(50), default="QR") # QR, Manual, Geo
    notes = Column(String(255), nullable=True)

    gym = relationship("Gym", back_populates="attendance")
    member = relationship("Member", back_populates="attendance")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    member_id = Column(Integer, ForeignKey("members.id"))
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    service_name = Column(String(200), default="Membership / Service")
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.0)
    total_amount = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(String(50), default="paid") # paid, pending, cancelled
    payment_mode = Column(String(50), default="UPI")
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="invoices")
    member = relationship("Member", back_populates="invoices")


class ServicePlan(Base):
    __tablename__ = "service_plans"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    name = Column(String(200), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    duration_days = Column(Integer, default=30)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="plans")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), index=True, nullable=False)
    token = Column(String(100), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())


class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(15), index=True, nullable=False)
    otp = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)
    resend_count = Column(Integer, default=0)
    last_sent_at = Column(DateTime, default=func.now())
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    actor_name = Column(String(100), default="Owner") # Staff/Owner name
    action = Column(String(100), nullable=False) # e.g. "RECORD_PAYMENT", "UPDATE_MEMBER", "GENERATE_INVOICE"
    target_type = Column(String(50), nullable=True) # "member", "payment", "invoice", "staff"
    target_id = Column(Integer, nullable=True)
    details = Column(String(500), nullable=False)
    ip_address = Column(String(50), default="127.0.0.1")
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="audit_logs")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    customer_name = Column(String(200), nullable=False)
    customer_phone = Column(String(15), nullable=True)
    rating = Column(Integer, nullable=False) # 1-5
    feedback_text = Column(String(1000), nullable=True)
    sentiment = Column(String(20), default="POSITIVE") # POSITIVE / CRITICAL
    is_google_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="reviews")


class BookingSlot(Base):
    __tablename__ = "booking_slots"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    service_name = Column(String(200), nullable=False)
    time_slot = Column(String(100), nullable=False) # e.g. "06:00 AM - 07:00 AM"
    capacity = Column(Integer, default=20)
    booked_count = Column(Integer, default=0)
    slot_date = Column(Date, default=func.current_date())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="booking_slots")


class DocumentRecord(Base):
    __tablename__ = "document_records"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    doc_type = Column(String(50), default="Agreement") # Prescription, Medical Report, Agreement, Job Card, ID Proof
    title = Column(String(200), nullable=False)
    file_url = Column(String(500), nullable=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="documents")


class CustomerTimelineEvent(Base):
    __tablename__ = "customer_timeline_events"

    id = Column(Integer, primary_key=True, index=True)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    member_id = Column(Integer, ForeignKey("members.id"))
    event_type = Column(String(50), nullable=False) # LEAD_CAPTURED, TRIAL_BOOKED, PAYMENT_RECEIVED, QR_CHECKIN, RENEWAL_DUE
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    staff_name = Column(String(100), default="AutoBiz AI")
    amount = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime, default=func.now())

    gym = relationship("Gym", back_populates="timeline_events")


class BulkSubscriptionPayment(Base):
    __tablename__ = "bulk_subscription_payments"

    id = Column(Integer, primary_key=True, index=True)
    owner_email = Column(String(200), index=True, nullable=False)
    total_branches = Column(Integer, default=1)
    total_amount = Column(Numeric(10, 2), nullable=False)
    utr_number = Column(String(100), nullable=False)
    status = Column(String(20), default="pending") # pending, verified, rejected
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now())