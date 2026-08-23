from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

# --- Business & Auth Schemas ---

class BusinessRegister(BaseModel):
    name: str
    owner_name: str
    phone: str
    email: str
    password: str
    business_type: Optional[str] = "gym"
    city: Optional[str] = None

class BusinessLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    business_id: int
    business_name: str
    business_type: str

class GymResponse(BaseModel):
    id: int
    name: str
    owner_name: str
    phone: str
    email: Optional[str] = None
    business_type: Optional[str] = "gym"
    city: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Member Schemas ---

class MemberCreate(BaseModel):
    gym_id: int
    full_name: str
    phone: str
    email: Optional[str] = None
    membership_type: Optional[str] = "monthly"
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class MemberResponse(BaseModel):
    id: int
    gym_id: int
    full_name: str
    phone: str
    email: Optional[str] = None
    membership_type: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Lead Schemas ---

class LeadCreate(BaseModel):
    gym_id: int
    name: str
    phone: str
    email: Optional[str] = None
    source: Optional[str] = "website"
    notes: Optional[str] = None
    trial_date: Optional[datetime] = None

class LeadUpdateStatus(BaseModel):
    status: str
    notes: Optional[str] = None
    trial_date: Optional[datetime] = None

class LeadResponse(BaseModel):
    id: int
    gym_id: int
    name: str
    phone: str
    email: Optional[str] = None
    source: str
    status: str
    trial_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Payment Schemas ---

class PaymentCreate(BaseModel):
    gym_id: int
    member_id: int
    amount: Decimal
    payment_mode: Optional[str] = "UPI"
    payment_status: Optional[str] = "completed"
    payment_date: Optional[date] = None
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    gym_id: int
    member_id: int
    amount: Decimal
    payment_mode: str
    payment_status: str
    payment_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RevenueSummaryResponse(BaseModel):
    gym_id: int
    total_revenue: Decimal
    total_transactions: int
