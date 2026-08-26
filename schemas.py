from pydantic import BaseModel, EmailStr
from typing import Optional, List
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
    upi_id: Optional[str] = None
    subscription_status: Optional[str] = "trial"
    subscription_start: Optional[date] = None
    subscription_end: Optional[date] = None
    subscription_plan: Optional[str] = "monthly"
    created_at: datetime

    class Config:
        from_attributes = True

class PlatformSubscriptionStatus(BaseModel):
    gym_id: int
    gym_name: str
    status: str # trial, active, expired
    plan: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days_remaining: int
    is_locked: bool
    platform_upi_id: str
    monthly_price: Decimal

class PlatformRenewRequest(BaseModel):
    gym_id: int
    plan_name: Optional[str] = "Monthly SaaS Plan"
    amount: Decimal = Decimal("1500.00")
    utr_number: Optional[str] = None

class AdminExtendSubscriptionRequest(BaseModel):
    gym_id: int
    months: int = 1
    status: Optional[str] = "active"


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
    time_slot: Optional[str] = None

class LeadUpdateStatus(BaseModel):
    status: str
    notes: Optional[str] = None
    trial_date: Optional[datetime] = None
    time_slot: Optional[str] = None

class LeadResponse(BaseModel):
    id: int
    gym_id: int
    name: str
    phone: str
    email: Optional[str] = None
    source: str
    status: str
    trial_date: Optional[datetime] = None
    time_slot: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SlotInfo(BaseModel):
    slot: str
    booked_count: int
    max_capacity: int
    is_available: bool
    label: str

class GymSlotsResponse(BaseModel):
    gym_id: int
    date: str
    slots: List[SlotInfo]


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

class CustomerPaymentConfirm(BaseModel):
    phone: str
    gym_id: int
    plan_name: str
    amount: Decimal
    utr_number: Optional[str] = None
    payment_mode: Optional[str] = "UPI"

class RevenueSummaryResponse(BaseModel):
    gym_id: int
    total_revenue: Decimal
    total_transactions: int


# --- Password Reset Schemas ---

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# --- Staff & RBAC Schemas ---

class StaffCreate(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    role: Optional[str] = "trainer" # owner, manager, receptionist, trainer
    password: Optional[str] = "staff123"

class StaffResponse(BaseModel):
    id: int
    gym_id: int
    full_name: str
    phone: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Attendance & QR Schemas ---

class AttendanceCheckIn(BaseModel):
    phone: Optional[str] = None
    member_id: Optional[int] = None
    method: Optional[str] = "QR" # QR, Manual, Geo
    notes: Optional[str] = None

class AttendanceResponse(BaseModel):
    id: int
    gym_id: int
    member_id: int
    member_name: Optional[str] = None
    member_phone: Optional[str] = None
    check_in_time: datetime
    method: str
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# --- Invoice Schemas ---

class InvoiceCreate(BaseModel):
    member_id: int
    payment_id: Optional[int] = None
    service_name: Optional[str] = "Monthly Membership / Service"
    subtotal: Decimal
    tax_amount: Optional[Decimal] = Decimal("0.00")
    total_amount: Decimal
    payment_mode: Optional[str] = "UPI"
    payment_status: Optional[str] = "paid"

class InvoiceResponse(BaseModel):
    id: int
    gym_id: int
    member_id: int
    member_name: Optional[str] = None
    member_phone: Optional[str] = None
    business_name: Optional[str] = None
    invoice_number: str
    service_name: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    payment_status: str
    payment_mode: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Service Plans Schemas ---

class ServicePlanCreate(BaseModel):
    name: str
    price: Decimal
    duration_days: Optional[int] = 30
    description: Optional[str] = None

class ServicePlanResponse(BaseModel):
    id: int
    gym_id: int
    name: str
    price: Decimal
    duration_days: int
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- AI Engine & Business OS Schemas ---

class AIQueryRequest(BaseModel):
    query: str

class AIQueryResponse(BaseModel):
    query: str
    answer: str
    action_type: Optional[str] = "info" # info, campaign, reminder, alert
    data_snapshot: Optional[dict] = None

class ChurnRiskMember(BaseModel):
    member_id: int
    name: str
    phone: str
    risk_score: int # 0-100%
    risk_level: str # HIGH, MEDIUM, LOW
    reason: str
    suggested_action: str

class AIBusinessInsightsResponse(BaseModel):
    revenue_growth_pct: float
    total_revenue_this_month: float
    active_members: int
    expiring_members_count: int
    inactive_members_count: int
    hot_leads_count: int
    churn_risk_members: List[ChurnRiskMember]
    smart_alerts: List[dict]
    recommended_campaign: dict

class AIOfferRequest(BaseModel):
    theme: Optional[str] = "Festive Special" # Festival, Monsoon, New Year, Summer, Flash Deal
    discount_pct: Optional[int] = 20
    target_audience: Optional[str] = "All Leads & Expired Members"

class AIOfferResponse(BaseModel):
    offer_title: str
    tagline: str
    whatsapp_message: str
    call_to_action: str


# --- Audit Log & Security Schemas ---

class AuditLogResponse(BaseModel):
    id: int
    gym_id: int
    actor_name: str
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    details: str
    ip_address: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Reviews & Reputation Schemas ---

class ReviewCreate(BaseModel):
    gym_id: Optional[int] = 1
    customer_name: str
    customer_phone: Optional[str] = None
    rating: int # 1 to 5
    feedback_text: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    gym_id: int
    customer_name: str
    customer_phone: Optional[str] = None
    rating: int
    feedback_text: Optional[str] = None
    sentiment: str
    is_google_shared: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Booking Slot Schemas ---

class BookingSlotCreate(BaseModel):
    service_name: str
    time_slot: str
    capacity: Optional[int] = 20

class BookingSlotResponse(BaseModel):
    id: int
    gym_id: int
    service_name: str
    time_slot: str
    capacity: int
    booked_count: int
    slot_date: date
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Multi-Branch Schemas ---

class BranchCreate(BaseModel):
    name: str
    business_type: str
    phone: str
    address_line: str
    state: str
    district: str
    city: str
    pincode: str
    timings: Optional[str] = "06:00 AM - 10:00 PM"
    upi_id: Optional[str] = None
    doctor_specialization: Optional[str] = None
    consultation_fee: Optional[Decimal] = Decimal("500.00")

class BranchResponse(BaseModel):
    id: int
    name: str
    owner_name: str
    owner_email: Optional[str] = None
    phone: str
    business_type: str
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    upi_id: Optional[str] = None
    subscription_status: str
    is_main_branch: bool
    total_members: Optional[int] = 0
    total_revenue: Optional[float] = 0.0
    pending_revenue: Optional[float] = 0.0

    class Config:
        from_attributes = True

class BulkSubscriptionRequest(BaseModel):
    owner_email: str
    utr_number: str
    total_branches: int
    total_amount: Decimal

# --- Timeline & Document Schemas ---

class TimelineEventCreate(BaseModel):
    member_id: int
    event_type: str
    title: str
    description: Optional[str] = None
    staff_name: Optional[str] = "Staff"
    amount: Optional[Decimal] = None

class TimelineEventResponse(BaseModel):
    id: int
    gym_id: int
    member_id: int
    event_type: str
    title: str
    description: Optional[str] = None
    staff_name: str
    amount: Optional[Decimal] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentCreate(BaseModel):
    member_id: Optional[int] = None
    doc_type: str
    title: str
    file_url: Optional[str] = None
    notes: Optional[str] = None

class DocumentResponse(BaseModel):
    id: int
    gym_id: int
    member_id: Optional[int] = None
    doc_type: str
    title: str
    file_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Customer Self-Booking Schemas ---

class CustomerSelfBookRequest(BaseModel):
    gym_id: int
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    service_or_plan_name: str
    booking_date: date
    time_slot: str
    amount: Decimal
    payment_mode: Optional[str] = "UPI"
    utr_number: Optional[str] = None
    notes: Optional[str] = None

# --- Role-Aware AI Assistant Schemas ---

class AIChatAssistantRequest(BaseModel):
    role: str = "customer" # "customer" or "owner"
    query: Optional[str] = None
    message: Optional[str] = None
    context_phone: Optional[str] = None # For customer looking up own membership
    gym_id: Optional[int] = None

class AIChatAssistantResponse(BaseModel):
    answer: str
    reply: Optional[str] = None
    role: str
    action_type: Optional[str] = "info"
    quick_links: Optional[List[dict]] = None


class OnboardingData(BaseModel):
    business_type: str
    timings: Optional[str] = "06:00 AM - 10:00 PM"
    upi_id: Optional[str] = None
    primary_service: Optional[str] = "Standard Membership"
    primary_price: Optional[Decimal] = Decimal("1000.00")




