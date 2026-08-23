from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
import os
import models
import schemas
import auth
import admin
import whatsapp_routes
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AutoBiz AI — Universal Business Automation SaaS", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Super Admin router
app.include_router(admin.router)
# Register WhatsApp AI router
app.include_router(whatsapp_routes.router)

@app.on_event("startup")
def on_app_startup():
    import scheduler
    scheduler.start_scheduler()

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


# --- Static / UI Routes ---
@app.get("/", tags=["UI"])
def serve_home():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/dashboard.html", tags=["UI"])
def serve_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/superadmin.html", tags=["UI"])
def serve_superadmin():
    return FileResponse(os.path.join(FRONTEND_DIR, "superadmin.html"))

@app.get("/explore.html", tags=["UI"])
def serve_explore():
    return FileResponse(os.path.join(FRONTEND_DIR, "explore.html"))

@app.get("/customer_portal.html", tags=["UI"])
def serve_customer_portal():
    return FileResponse(os.path.join(FRONTEND_DIR, "customer_portal.html"))

@app.get("/manifest.json", tags=["PWA"])
def serve_manifest():
    return FileResponse(os.path.join(FRONTEND_DIR, "manifest.json"), media_type="application/manifest+json")

@app.get("/sw.js", tags=["PWA"])
def serve_sw():
    return FileResponse(os.path.join(FRONTEND_DIR, "sw.js"), media_type="application/javascript")

# --- Public Business Discovery API ---
@app.get("/businesses/explore", tags=["Public Discovery"])
def explore_businesses(
    city: Optional[str] = None,
    business_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Gym)
    if city and city.lower() != "all":
        query = query.filter(models.Gym.city.ilike(f"%{city}%"))
    if business_type and business_type.lower() != "all":
        query = query.filter(models.Gym.business_type == business_type.lower())
    if search:
        query = query.filter(
            (models.Gym.name.ilike(f"%{search}%")) |
            (models.Gym.city.ilike(f"%{search}%")) |
            (models.Gym.owner_name.ilike(f"%{search}%"))
        )
    
    gyms = query.all()
    results = []
    
    # Default visual assets & timings map
    defaults = {
        "gym": {"timings": "06:00 AM - 10:00 PM", "starting_price": "₹800/mo", "rating": 4.9, "badge": "Smart 3D Facility", "image": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=600&q=80"},
        "clinic": {"timings": "09:00 AM - 08:00 PM", "starting_price": "₹500 / Visit", "rating": 4.9, "badge": "Verified Doctor", "image": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=600&q=80"},
        "salon": {"timings": "10:00 AM - 09:00 PM", "starting_price": "₹300 / Service", "rating": 4.8, "badge": "Top Rated Spa", "image": "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=600&q=80"},
        "coaching": {"timings": "08:00 AM - 07:00 PM", "starting_price": "₹1,200/mo", "rating": 4.9, "badge": "Expert Faculty", "image": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?auto=format&fit=crop&w=600&q=80"},
        "dental": {"timings": "09:30 AM - 08:30 PM", "starting_price": "₹400 / Checkup", "rating": 4.9, "badge": "Painless Care", "image": "https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=600&q=80"},
        "cafe": {"timings": "11:00 AM - 11:00 PM", "starting_price": "₹200 avg", "rating": 4.7, "badge": "Table Booking", "image": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=600&q=80"},
        "service": {"timings": "09:00 AM - 07:00 PM", "starting_price": "₹350 / Checkup", "rating": 4.8, "badge": "Express Service", "image": "https://images.unsplash.com/photo-1486006920555-c77dce18193b?auto=format&fit=crop&w=600&q=80"},
        "realestate": {"timings": "10:00 AM - 07:00 PM", "starting_price": "Free Site Visit", "rating": 4.9, "badge": "Verified Properties", "image": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=600&q=80"}
    }
    
    for g in gyms:
        btype = (g.business_type or "gym").lower()
        meta = defaults.get(btype, defaults["gym"])
        results.append({
            "id": g.id,
            "name": g.name,
            "owner_name": g.owner_name,
            "business_type": btype,
            "city": g.city or "Guwahati",
            "phone": g.phone,
            "upi_id": g.upi_id or "Not Set",
            "timings": meta["timings"],
            "starting_price": meta["starting_price"],
            "rating": meta["rating"],
            "badge": meta["badge"],
            "image": meta["image"]
        })
        
    return results


# --- Auth ---
@app.post("/auth/register", response_model=schemas.GymResponse, tags=["Authentication"])
def register_business(data: schemas.BusinessRegister, db: Session = Depends(get_db)):
    existing = db.query(models.Gym).filter(models.Gym.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pwd = auth.get_password_hash(data.password)
    db_business = models.Gym(
        name=data.name,
        owner_name=data.owner_name,
        phone=data.phone,
        email=data.email,
        password_hash=hashed_pwd,
        business_type=data.business_type or "gym",
        city=data.city,
        subscription_status="trial"
    )
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    return db_business

@app.post("/auth/login", response_model=schemas.Token, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    business = db.query(models.Gym).filter(models.Gym.email == form_data.username).first()
    if not business or not business.password_hash or not auth.verify_password(form_data.password, business.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    access_token = auth.create_access_token(data={"sub": business.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "business_id": business.id,
        "business_name": business.name,
        "business_type": business.business_type or "gym"
    }

# --- Member/Customer OTP Login ---
from pydantic import BaseModel
import random
from whatsapp_cloud import send_whatsapp_message
import asyncio

MOCK_OTP_STORE = {}

class OTPRequest(BaseModel):
    phone: str

class OTPVerify(BaseModel):
    phone: str
    otp: str

@app.post("/auth/member/request-otp", tags=["Authentication"])
async def request_member_otp(req: OTPRequest, db: Session = Depends(get_db)):
    # Generate 4-digit OTP
    otp = str(random.randint(1000, 9999))
    MOCK_OTP_STORE[req.phone] = otp
    
    # Send via WhatsApp AI Engine
    msg_text = f"🤖 AutoBiz Pass:\nAapka login OTP hai: *{otp}*\n\nApne portal me access ke liye ise darj karein! 🚀"
    await send_whatsapp_message(req.phone, msg_text, sender_name="AutoBiz Auth", channel="channel_2")
    
    return {"message": "OTP Sent via WhatsApp", "mock_otp": otp}

@app.post("/auth/member/verify-otp", tags=["Authentication"])
def verify_member_otp(req: OTPVerify, db: Session = Depends(get_db)):
    stored_otp = MOCK_OTP_STORE.get(req.phone)
    if not stored_otp or stored_otp != req.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Generate a simple token (In production, use JWT with phone payload)
    access_token = auth.create_access_token(data={"sub": req.phone, "role": "customer"})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "phone": req.phone
    }

from datetime import date

@app.get("/auth/member/status/{phone}", tags=["Authentication"])
def get_customer_status(phone: str, db: Session = Depends(get_db)):
    def gym_to_dict(g):
        return {"id": g.id, "name": g.name, "owner_name": g.owner_name, "phone": g.phone, "upi_id": g.upi_id or ""} if g else None

    # 1. Check if paying member
    member = db.query(models.Member).filter(models.Member.phone == phone).order_by(models.Member.id.desc()).first()
    if member:
        state = "ACTIVE_MEMBER"
        if member.end_date and member.end_date < date.today():
            state = "EXPIRED_MEMBER"
        gym = db.query(models.Gym).filter(models.Gym.id == member.gym_id).first()
        return {
            "phone": phone, "state": state,
            "data": {
                "id": member.id, "full_name": member.full_name, "phone": member.phone,
                "membership_type": member.membership_type or "Plan",
                "start_date": str(member.start_date) if member.start_date else None,
                "end_date": str(member.end_date) if member.end_date else None,
                "is_active": member.is_active
            },
            "gym_data": gym_to_dict(gym)
        }

    # 2. Check if lead/trial
    lead = db.query(models.Lead).filter(models.Lead.phone == phone).order_by(models.Lead.id.desc()).first()
    if lead:
        state = "TRIAL_BOOKED" if lead.status == "booked" else ("TRIAL_COMPLETED" if lead.status == "completed" else "NEW_LEAD")
        gym = db.query(models.Gym).filter(models.Gym.id == lead.gym_id).first()
        return {
            "phone": phone, "state": state,
            "data": {
                "id": lead.id, "name": lead.name, "phone": lead.phone,
                "status": lead.status, "notes": lead.notes,
                "trial_date": str(lead.trial_date) if lead.trial_date else None
            },
            "gym_data": gym_to_dict(gym)
        }

    # 3. Brand new customer
    return {"phone": phone, "state": "NEW_LEAD", "data": None, "gym_data": None}

@app.get("/auth/me", response_model=schemas.GymResponse, tags=["Authentication"])
def get_profile(current_user: models.Gym = Depends(auth.get_current_user)):
    return current_user


# --- Businesses ---
@app.get("/gyms", response_model=List[schemas.GymResponse], tags=["Businesses"])
def get_all(db: Session = Depends(get_db)):
    return db.query(models.Gym).all()

@app.get("/gyms/{gym_id}", response_model=schemas.GymResponse, tags=["Businesses"])
def get_one(gym_id: int, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    return gym


# --- Members ---
@app.post("/members/add", response_model=schemas.MemberResponse, tags=["Members"])
def add_member(member: schemas.MemberCreate, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == member.gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    db_member = models.Member(
        gym_id=member.gym_id, full_name=member.full_name,
        phone=member.phone, email=member.email,
        membership_type=member.membership_type,
        start_date=member.start_date, end_date=member.end_date
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

@app.get("/members", response_model=List[schemas.MemberResponse], tags=["Members"])
def all_members(db: Session = Depends(get_db)):
    return db.query(models.Member).all()

@app.get("/gyms/{gym_id}/members", response_model=List[schemas.MemberResponse], tags=["Members"])
def gym_members(gym_id: int, db: Session = Depends(get_db)):
    return db.query(models.Member).filter(models.Member.gym_id == gym_id).all()


# --- Leads ---
@app.post("/leads/create", response_model=schemas.LeadResponse, tags=["Leads"])
async def create_lead(lead: schemas.LeadCreate, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == lead.gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    db_lead = models.Lead(
        gym_id=lead.gym_id, name=lead.name, phone=lead.phone,
        email=lead.email, source=lead.source, notes=lead.notes,
        status="booked", trial_date=lead.trial_date
    )
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)

    # 🚀 AI WhatsApp Hook: Trial Booked
    gym_name = gym.name if gym else "our club"
    msg = f"Hey {lead.name}! 🎉\n\nYour Free Trial at {gym_name} has been successfully booked!\n\n📍 We've saved your spot. See you soon!\n(Reply if you need to reschedule)"
    await send_whatsapp_message(lead.phone, msg, sender_name=gym_name, channel="channel_2")

    return db_lead

@app.get("/gyms/{gym_id}/leads", response_model=List[schemas.LeadResponse], tags=["Leads"])
def gym_leads(gym_id: int, db: Session = Depends(get_db)):
    return db.query(models.Lead).filter(models.Lead.gym_id == gym_id).all()

@app.patch("/leads/{lead_id}/status", response_model=schemas.LeadResponse, tags=["Leads"])
async def update_lead(lead_id: int, update_data: schemas.LeadUpdateStatus, db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    old_status = lead.status
    lead.status = update_data.status
    if update_data.notes:
        lead.notes = update_data.notes
    if update_data.trial_date:
        lead.trial_date = update_data.trial_date
        
    db.commit()
    db.refresh(lead)

    # 🚀 AI WhatsApp Hook: Trial Completed -> Upsell Membership
    if old_status != "completed" and lead.status == "completed":
        gym = db.query(models.Gym).filter(models.Gym.id == lead.gym_id).first()
        gym_name = gym.name if gym else "our club"
        msg = f"Hey {lead.name}! 🔥\n\nHope you enjoyed your workout session at {gym_name} today!\n\nReady to crush your goals? 💪 We have special membership offers unlocked just for you.\n\nClick here to choose your plan and activate your digital ID instantly: http://127.0.0.1:8000/explore.html\n\nSee you tomorrow!"
        await send_whatsapp_message(lead.phone, msg, sender_name=gym_name, channel="channel_2")

    return lead


# --- Payments ---
@app.post("/payments/create", response_model=schemas.PaymentResponse, tags=["Payments"])
def record_payment(payment: schemas.PaymentCreate, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == payment.gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    member = db.query(models.Member).filter(models.Member.id == payment.member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db_payment = models.Payment(
        gym_id=payment.gym_id, member_id=payment.member_id,
        amount=payment.amount, payment_mode=payment.payment_mode or "UPI",
        payment_status=payment.payment_status or "completed",
        payment_date=payment.payment_date, notes=payment.notes
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@app.get("/gyms/{gym_id}/payments", response_model=List[schemas.PaymentResponse], tags=["Payments"])
def gym_payments(gym_id: int, db: Session = Depends(get_db)):
    return db.query(models.Payment).filter(models.Payment.gym_id == gym_id).all()

@app.get("/gyms/{gym_id}/revenue", response_model=schemas.RevenueSummaryResponse, tags=["Payments"])
def gym_revenue(gym_id: int, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    total = db.query(func.sum(models.Payment.amount)).filter(
        models.Payment.gym_id == gym_id, models.Payment.payment_status == "completed"
    ).scalar() or Decimal("0.00")
    count = db.query(func.count(models.Payment.id)).filter(
        models.Payment.gym_id == gym_id, models.Payment.payment_status == "completed"
    ).scalar() or 0
    return schemas.RevenueSummaryResponse(gym_id=gym_id, total_revenue=total, total_transactions=count)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")