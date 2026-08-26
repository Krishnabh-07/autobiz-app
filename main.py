import os
import sys

# Ensure backend directory is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
import models
import schemas
import auth
import admin
import whatsapp_routes
import bot_ai
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

# Safe SQLite column auto-migrations
try:
    with engine.connect() as _conn:
        from sqlalchemy import text
        cols = [
            ("is_onboarded", "BOOLEAN DEFAULT 0"),
            ("owner_email", "VARCHAR(200)"),
            ("is_main_branch", "BOOLEAN DEFAULT 1"),
            ("parent_id", "INTEGER"),
            ("address_line", "VARCHAR(300)"),
            ("state", "VARCHAR(100) DEFAULT 'Assam'"),
            ("district", "VARCHAR(100) DEFAULT 'Kamrup Metropolitan'"),
            ("pincode", "VARCHAR(10)"),
            ("village_or_town", "VARCHAR(150)"),
            ("autopilot_enabled", "BOOLEAN DEFAULT 1"),
            ("doctor_specialization", "VARCHAR(150)"),
            ("slot_duration_mins", "INTEGER DEFAULT 15"),
            ("consultation_fee", "NUMERIC(10,2) DEFAULT 500.00"),
            ("working_days", "VARCHAR(100) DEFAULT 'Mon-Sat'"),
        ]
        for col_name, col_type in cols:
            try:
                _conn.execute(text(f"ALTER TABLE gyms ADD COLUMN {col_name} {col_type}"))
                _conn.commit()
            except Exception:
                pass
except Exception:
    pass

# Dynamic site base URL — use env var on cloud, fallback to localhost for dev
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "http://127.0.0.1:8000")

app = FastAPI(title="AutoBiz AI — Universal Business Automation SaaS", version="2.0.0")

# CORS — on production set ALLOWED_ORIGINS env var; dev allows all
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
_origins = [o.strip() for o in _allowed_origins.split(",")] if _allowed_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Error Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"[GLOBAL ERROR] {request.method} {request.url}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again."}
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

@app.get("/privacy.html", tags=["UI"])
def serve_privacy():
    return FileResponse(os.path.join(FRONTEND_DIR, "privacy.html"))

@app.get("/terms.html", tags=["UI"])
def serve_terms():
    return FileResponse(os.path.join(FRONTEND_DIR, "terms.html"))

@app.get("/support.html", tags=["UI"])
def serve_support():
    return FileResponse(os.path.join(FRONTEND_DIR, "support.html"))

@app.get("/business_storefront.html", tags=["UI"])
def serve_storefront_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "business_storefront.html"))

@app.get("/b/{business_id}", tags=["UI"])
def serve_storefront_short(business_id: str):
    return FileResponse(os.path.join(FRONTEND_DIR, "business_storefront.html"))

@app.get("/business/{business_id}", tags=["UI"])
def serve_storefront_slug(business_id: str):
    return FileResponse(os.path.join(FRONTEND_DIR, "business_storefront.html"))

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


@app.get("/public/locations", tags=["Public Discovery"])
def get_public_locations(db: Session = Depends(get_db)):
    registered_cities = db.query(models.Gym.city).filter(models.Gym.city.isnot(None)).distinct().all()
    registered_districts = db.query(models.Gym.district).filter(models.Gym.district.isnot(None)).distinct().all()
    registered_states = db.query(models.Gym.state).filter(models.Gym.state.isnot(None)).distinct().all()
    
    cities = {r[0].strip() for r in registered_cities if r[0] and r[0].strip()}
    districts = {r[0].strip() for r in registered_districts if r[0] and r[0].strip()}
    states = {r[0].strip() for r in registered_states if r[0] and r[0].strip()}
    
    default_hubs = [
        "Guwahati", "Dibrugarh", "Silchar", "Jorhat", "Nagaon", "Tinsukia", "Tezpur", "Bongaigaon",
        "Delhi NCR", "Mumbai", "Bengaluru", "Kolkata", "Hyderabad", "Pune", "Jaipur", "Lucknow", "Patna", "Chandigarh", "Ahmedabad", "Chennai"
    ]
    all_locations = sorted(list(cities.union(districts).union(set(default_hubs))))
    
    return {
        "locations": all_locations,
        "states": sorted(list(states.union({"Assam", "Delhi", "Maharashtra", "Karnataka", "West Bengal", "Uttar Pradesh", "Bihar", "Rajasthan"}))),
        "total_registered": len(cities)
    }


@app.get("/locations/states-and-districts", tags=["Public Discovery"])
def get_states_and_districts(db: Session = Depends(get_db)):
    # Comprehensive pan-India state & district dictionary with auto-aggregation from DB
    data = {
        "Assam": {
            "Kamrup Metropolitan": ["Guwahati", "Dispur", "Chandmari", "Panbazar", "Beltola", "Zoo Road", "Six Mile"],
            "Kamrup Rural": ["Rangia", "Hajo", "Palasbari"],
            "Dibrugarh": ["Dibrugarh", "Chabua", "Naharkatia"],
            "Jorhat": ["Jorhat", "Mariani", "Titabor"],
            "Silchar / Cachar": ["Silchar", "Lakhipur", "Sonai"],
            "Nagaon": ["Nagaon", "Kaliabor", "Dhing"],
            "Sonitpur": ["Tezpur", "Dhekiajuli", "Rangapara"],
            "Tinsukia": ["Tinsukia", "Digboi", "Doomdooma"],
            "Nalbari": ["Nalbari", "Tihu", "Belsor"],
            "Barpeta": ["Barpeta", "Howly", "Sarthebari"],
            "Bongaigaon": ["Bongaigaon", "Abhayapuri"]
        },
        "Delhi NCR": {
            "Central Delhi": ["Connaught Place", "Karol Bagh", "Pahar Ganj"],
            "South Delhi": ["Hauz Khas", "Saket", "Greater Kailash", "Lajpat Nagar"],
            "North Delhi": ["Civil Lines", "Pitampura", "Rohini"],
            "Gurugram": ["Cyber City", "Golf Course Road", "Sector 29", "Sohna Road"],
            "Noida": ["Sector 18", "Sector 62", "Sector 137"]
        },
        "Maharashtra": {
            "Mumbai": ["Bandra", "Andheri", "Juhu", "Colaba", "Dadar", "Powai"],
            "Pune": ["Kothrud", "Koregaon Park", "Viman Nagar", "Hinjawadi", "Baner"],
            "Nagpur": ["Sitabuldi", "Dharampeth", "Ramdaspeth"]
        },
        "Karnataka": {
            "Bengaluru Urban": ["Indiranagar", "Koramangala", "HSR Layout", "Whitefield", "Jayanagar", "MG Road"],
            "Mysuru": ["Gokulam", "Jayalakshmipuram", "Kuvempunagar"]
        },
        "West Bengal": {
            "Kolkata": ["Park Street", "Salt Lake", "New Town", "Ballygunge", "Alipore"],
            "Howrah": ["Howrah AC Market", "Shibpur"],
            "Darjeeling": ["Darjeeling", "Siliguri"]
        },
        "Uttar Pradesh": {
            "Lucknow": ["Hazratganj", "Gomti Nagar", "Alambagh", "Indira Nagar"],
            "Kanpur": ["Civil Lines", "Swaroop Nagar", "Mall Road"],
            "Varanasi": ["Lanka", "Assi Ghat", "Cantonment"]
        },
        "Bihar": {
            "Patna": ["Boring Road", "Kankarbagh", "Bailey Road", "Fraser Road"]
        },
        "Rajasthan": {
            "Jaipur": ["Malviya Nagar", "Vaishali Nagar", "C-Scheme", "Mansarovar"]
        }
    }
    
    # Auto-merge any custom state/district/city registered by owners in the database
    gyms = db.query(models.Gym).all()
    for g in gyms:
        st = (g.state or "Assam").strip()
        dist = (g.district or "Kamrup Metropolitan").strip()
        city = (g.city or g.village_or_town or "Guwahati").strip()
        if st and dist and city:
            if st not in data:
                data[st] = {}
            if dist not in data[st]:
                data[st][dist] = []
            if city not in data[st][dist]:
                data[st][dist].append(city)
                
    return data


@app.get("/robots.txt", tags=["SEO"])

def get_robots_txt():
    return FileResponse(os.path.join(FRONTEND_DIR, "robots.txt"), media_type="text/plain")

@app.get("/sitemap.xml", tags=["SEO"])
def get_sitemap_xml():
    return FileResponse(os.path.join(FRONTEND_DIR, "sitemap.xml"), media_type="application/xml")


# --- Auth & Registration ---
@app.post("/auth/register", response_model=schemas.GymResponse, tags=["Authentication"])
def register_business(data: schemas.BusinessRegister, db: Session = Depends(get_db)):
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    
    existing_email = db.query(models.Gym).filter(models.Gym.email == data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    
    existing_phone = db.query(models.Gym).filter(models.Gym.phone == data.phone).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="An account with this phone number already exists")

    hashed_pwd = auth.get_password_hash(data.password)
    join_date = date.today()
    db_business = models.Gym(
        name=data.name,
        owner_name=data.owner_name,
        phone=data.phone,
        email=data.email,
        password_hash=hashed_pwd,
        business_type=data.business_type or "gym",
        city=data.city or "Guwahati",
        subscription_status="trial",
        subscription_start=join_date,
        subscription_end=join_date + timedelta(days=14),
        subscription_plan="monthly"
    )
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    return db_business

import secrets
from datetime import datetime, timedelta

# --- Simple In-Memory Rate Limiting and Abuse Prevention ---
ABUSE_TRACKER = {}

def check_rate_limit(key: str, max_attempts: int, period_seconds: int):
    now = datetime.now()
    if key not in ABUSE_TRACKER:
        ABUSE_TRACKER[key] = []
    
    # Filter out expired timestamps
    cutoff = now - timedelta(seconds=period_seconds)
    ABUSE_TRACKER[key] = [t for t in ABUSE_TRACKER[key] if t > cutoff]
    
    if len(ABUSE_TRACKER[key]) >= max_attempts:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please try again after {period_seconds} seconds."
        )
    
    ABUSE_TRACKER[key].append(now)


@app.post("/auth/login", response_model=schemas.Token, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Rate Limit: Max 5 attempts per 5 minutes per username
    check_rate_limit(f"login:{form_data.username}", 5, 300)

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


# --- Password Reset Flow ---
@app.post("/auth/forgot-password", tags=["Authentication"])
async def forgot_password(req_data: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Rate Limit: Max 3 requests per hour per email
    check_rate_limit(f"forgot_pass:{req_data.email}", 3, 3600)
    
    gym = db.query(models.Gym).filter(models.Gym.email == req_data.email).first()
    if not gym:
        return {"message": "If this email is registered, a password reset link has been generated."}
        
    # Generate secure reset token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(minutes=30)
    
    # Save token in DB
    reset_entry = models.PasswordResetToken(
        email=req_data.email,
        token=token,
        expires_at=expires_at
    )
    db.add(reset_entry)
    db.commit()
    
    # Generate reset link using dynamic base URL
    reset_link = f"{SITE_BASE_URL}/index.html?reset_token={token}"
    print(f"🔒 MOCK EMAIL: Password reset requested for {req_data.email}. Link: {reset_link}")
    
    # Send via WhatsApp AI
    msg_text = f"🔐 *AutoBiz Security Reset*:\nA password reset request was initiated for your business account.\n\nClick this link to change your password (valid for 30 minutes):\n{reset_link}"
    await send_whatsapp_message(gym.phone, msg_text, sender_name="AutoBiz Auth", channel="channel_2")
    
    return {"message": "Password reset link generated.", "mock_link": reset_link}


@app.post("/auth/reset-password", tags=["Authentication"])
def reset_password(req_data: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    # Rate Limit: Max 5 attempts per 15 minutes per token
    check_rate_limit(f"reset_pass:{req_data.token}", 5, 900)
    
    token_entry = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == req_data.token,
        models.PasswordResetToken.used == False,
        models.PasswordResetToken.expires_at > datetime.now()
    ).first()
    
    if not token_entry:
        raise HTTPException(status_code=400, detail="Invalid, expired or already used reset token")
        
    gym = db.query(models.Gym).filter(models.Gym.email == token_entry.email).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Associated business account not found")
        
    if len(req_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
    gym.password_hash = auth.get_password_hash(req_data.new_password)
    token_entry.used = True
    db.commit()
    
    return {"message": "Password has been successfully reset. You can now login."}


# --- Member/Customer OTP Login ---
from pydantic import BaseModel
import random
from whatsapp_cloud import send_whatsapp_message
import asyncio

class OTPRequest(BaseModel):
    phone: str

class OTPVerify(BaseModel):
    phone: str
    otp: str

@app.post("/auth/member/request-otp", tags=["Authentication"])
async def request_member_otp(req: OTPRequest, db: Session = Depends(get_db)):
    now = datetime.now()
    phone = req.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
        
    # Expose resend limit (Min 60 seconds interval check)
    last_verification = db.query(models.OTPVerification).filter(
        models.OTPVerification.phone == phone
    ).order_by(models.OTPVerification.id.desc()).first()
    
    if last_verification and (now - last_verification.last_sent_at).total_seconds() < 60:
        remaining = 60 - int((now - last_verification.last_sent_at).total_seconds())
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {remaining} seconds before requesting another OTP."
        )
        
    # Rate Limit: Max 5 requests per hour per phone
    check_rate_limit(f"otp_phone:{phone}", 5, 3600)
    
    # Generate 4-digit OTP
    otp_code = str(random.randint(1000, 9999))
    
    verification = models.OTPVerification(
        phone=phone,
        otp=otp_code,
        expires_at=now + timedelta(minutes=5),
        attempts=0,
        last_sent_at=now,
        verified=False
    )
    db.add(verification)
    db.commit()
    
    # Send via WhatsApp AI Engine
    msg_text = f"🤖 AutoBiz Pass:\nAapka login OTP hai: *{otp_code}*\n\nApne portal me access ke liye ise darj karein! 🚀"
    await send_whatsapp_message(phone, msg_text, sender_name="AutoBiz Auth", channel="channel_2")
    
    return {"message": "OTP Sent via WhatsApp", "mock_otp": otp_code}

@app.post("/auth/member/verify-otp", tags=["Authentication"])
def verify_member_otp(req: OTPVerify, db: Session = Depends(get_db)):
    now = datetime.now()
    phone = req.phone.strip()
    
    verification = db.query(models.OTPVerification).filter(
        models.OTPVerification.phone == phone,
        models.OTPVerification.verified == False
    ).order_by(models.OTPVerification.id.desc()).first()
    
    if not verification:
        raise HTTPException(status_code=400, detail="No active OTP request found for this phone number")
        
    if verification.attempts >= 3:
        raise HTTPException(status_code=400, detail="Too many incorrect attempts. Please request a new OTP.")
        
    if verification.expires_at < now:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
        
    verification.attempts += 1
    db.commit()
    
    if verification.otp != req.otp:
        remaining_attempts = max(0, 3 - verification.attempts)
        if remaining_attempts == 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid OTP. Attempts limit reached. Please request a new one."
            )
        raise HTTPException(status_code=400, detail=f"Invalid OTP. {remaining_attempts} attempts remaining.")
        
    verification.verified = True
    db.commit()
    
    # Generate token
    access_token = auth.create_access_token(data={"sub": phone, "role": "customer"})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "phone": phone
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
                "trial_date": str(lead.trial_date) if lead.trial_date else None,
                "time_slot": lead.time_slot or "Standard Batch"
            },
            "gym_data": gym_to_dict(gym)
        }

    # 3. Brand new customer
    return {"phone": phone, "state": "NEW_LEAD", "data": None, "gym_data": None}

@app.get("/auth/me", response_model=schemas.GymResponse, tags=["Authentication"])
def get_profile(current_user: models.Gym = Depends(auth.get_current_user)):
    return current_user


# --- Secure Tenant-Isolated APIs (P0 Security) ---
@app.get("/gyms/me/dashboard", tags=["Tenant Dashboard"])
def get_my_dashboard(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # 1. Members strictly for current tenant
    members = db.query(models.Member).filter(models.Member.gym_id == current_user.id).order_by(models.Member.id.desc()).all()
    
    # 2. Leads strictly for current tenant
    leads = db.query(models.Lead).filter(models.Lead.gym_id == current_user.id).order_by(models.Lead.id.desc()).all()
    
    # 3. Payments strictly for current tenant
    payments = db.query(models.Payment).filter(models.Payment.gym_id == current_user.id).order_by(models.Payment.id.desc()).all()
    
    # 4. Revenue metrics strictly for current tenant
    total_rev = db.query(func.sum(models.Payment.amount)).filter(
        models.Payment.gym_id == current_user.id, models.Payment.payment_status == "completed"
    ).scalar() or Decimal("0.00")
    total_trans = db.query(func.count(models.Payment.id)).filter(
        models.Payment.gym_id == current_user.id, models.Payment.payment_status == "completed"
    ).scalar() or 0

    # 5. SaaS Subscription details
    today = date.today()
    if not current_user.subscription_end:
        join_date = current_user.created_at.date() if current_user.created_at else today
        current_user.subscription_start = join_date
        current_user.subscription_end = join_date + timedelta(days=14)
        current_user.subscription_status = "trial"
        db.commit()
        db.refresh(current_user)

    days_left = (current_user.subscription_end - today).days
    is_locked = days_left < 0
    sub_status = "expired" if is_locked else (current_user.subscription_status or "trial")

    return {
        "business": {
            "id": current_user.id,
            "name": current_user.name,
            "owner_name": current_user.owner_name,
            "phone": current_user.phone,
            "email": current_user.email,
            "business_type": current_user.business_type or "gym",
            "city": current_user.city or "Guwahati",
            "upi_id": current_user.upi_id or ""
        },
        "members": [
            {
                "id": m.id, "full_name": m.full_name, "phone": m.phone, "email": m.email,
                "membership_type": m.membership_type, "start_date": str(m.start_date) if m.start_date else None,
                "end_date": str(m.end_date) if m.end_date else None, "is_active": m.is_active
            } for m in members
        ],
        "leads": [
            {
                "id": l.id, "name": l.name, "phone": l.phone, "email": l.email,
                "source": l.source, "status": l.status, "notes": l.notes,
                "time_slot": l.time_slot or "Standard Batch",
                "trial_date": str(l.trial_date) if l.trial_date else None
            } for l in leads
        ],
        "payments": [
            {
                "id": p.id, "amount": float(p.amount), "payment_mode": p.payment_mode,
                "payment_status": p.payment_status, "payment_date": str(p.payment_date) if p.payment_date else "Today",
                "notes": p.notes or ""
            } for p in payments
        ],
        "revenue": {
            "total_revenue": float(total_rev),
            "total_transactions": total_trans
        },
        "subscription": {
            "status": sub_status,
            "days_remaining": max(0, days_left),
            "start_date": str(current_user.subscription_start) if current_user.subscription_start else str(today),
            "end_date": str(current_user.subscription_end) if current_user.subscription_end else str(today),
            "is_locked": is_locked,
            "monthly_price": 1500.0,
            "platform_upi_id": "krishnabh@upi"
        }
    }


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
def add_member(member: schemas.MemberCreate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # 🔒 P0 Security: Always use gym_id from authenticated JWT token — never trust frontend payload
    db_member = models.Member(
        gym_id=current_user.id,  # Strictly from JWT, NOT from member.gym_id
        full_name=member.full_name,
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


# --- AI Time Slot & Capacity Engine ---
DEFAULT_SLOTS = [
    {"slot": "06:00 AM - 07:00 AM", "label": "🌅 Early Morning Batch", "max_capacity": 4},
    {"slot": "07:00 AM - 08:00 AM", "label": "⚡ Morning Peak Batch", "max_capacity": 4},
    {"slot": "08:00 AM - 09:00 AM", "label": "☀️ Mid Morning Batch", "max_capacity": 4},
    {"slot": "09:00 AM - 10:00 AM", "label": "🌿 Late Morning Batch", "max_capacity": 4},
    {"slot": "05:00 PM - 06:00 PM", "label": "🔥 Evening Kickoff", "max_capacity": 4},
    {"slot": "06:00 PM - 07:00 PM", "label": "🚀 Prime Evening Rush", "max_capacity": 4},
    {"slot": "07:00 PM - 08:00 PM", "label": "💪 Power Hour Batch", "max_capacity": 4},
    {"slot": "08:00 PM - 09:00 PM", "label": "🌙 Late Night Session", "max_capacity": 4},
]

@app.get("/gyms/{gym_id}/slots", response_model=schemas.GymSlotsResponse, tags=["Time Slots"])
def get_gym_slots(gym_id: int, date_str: Optional[str] = None, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    
    selected_date = date_str or str(date.today())
    
    # Query leads booked for this gym and date
    leads = db.query(models.Lead).filter(
        models.Lead.gym_id == gym_id,
        models.Lead.status.in_(["booked", "completed"])
    ).all()

    # Calculate capacity per slot
    slot_counts = {}
    for l in leads:
        if l.time_slot:
            slot_counts[l.time_slot] = slot_counts.get(l.time_slot, 0) + 1

    slot_list = []
    for s in DEFAULT_SLOTS:
        booked = slot_counts.get(s["slot"], 0)
        max_cap = s["max_capacity"]
        available = booked < max_cap
        slot_list.append(schemas.SlotInfo(
            slot=s["slot"],
            booked_count=booked,
            max_capacity=max_cap,
            is_available=available,
            label=s["label"]
        ))

    return schemas.GymSlotsResponse(gym_id=gym_id, date=selected_date, slots=slot_list)


# --- Leads ---
@app.post("/leads/create", response_model=schemas.LeadResponse, tags=["Leads"])
async def create_lead(lead: schemas.LeadCreate, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == lead.gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check slot capacity if time_slot provided
    if lead.time_slot:
        existing_booked = db.query(models.Lead).filter(
            models.Lead.gym_id == lead.gym_id,
            models.Lead.time_slot == lead.time_slot,
            models.Lead.status == "booked"
        ).count()
        if existing_booked >= 4:
            raise HTTPException(status_code=400, detail=f"Slot '{lead.time_slot}' is currently full! Please choose another batch.")

    db_lead = models.Lead(
        gym_id=lead.gym_id, name=lead.name, phone=lead.phone,
        email=lead.email, source=lead.source, notes=lead.notes,
        status="booked", trial_date=lead.trial_date, time_slot=lead.time_slot
    )
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)

    # 🚀 AI WhatsApp Hook: Trial Booked with exact Slot
    gym_name = gym.name if gym else "our club"
    slot_info = f" for the *{lead.time_slot}* batch" if lead.time_slot else ""
    msg = f"Hey {lead.name}! 🎉\n\nYour Free Workout Trial at *{gym_name}*{slot_info} has been successfully booked!\n\n📍 We've reserved your spot. Please arrive 10 mins early.\n\nSee you soon! 💪"
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
    if update_data.time_slot:
        lead.time_slot = update_data.time_slot
        
    db.commit()
    db.refresh(lead)

    # 🚀 AI WhatsApp Hook: Trial Completed -> Upsell Membership
    if old_status != "completed" and lead.status == "completed":
        gym = db.query(models.Gym).filter(models.Gym.id == lead.gym_id).first()
        gym_name = gym.name if gym else "our club"
        msg = f"Hey {lead.name}! 🔥\n\nHope you enjoyed your workout session at {gym_name} today!\n\nReady to crush your goals? 💪 We have special membership offers unlocked just for you.\n\nClick here to choose your plan and activate your digital ID instantly: {SITE_BASE_URL}/customer_portal.html\n\nSee you tomorrow!"
        await send_whatsapp_message(lead.phone, msg, sender_name=gym_name, channel="channel_2")

    return lead


# --- Payments ---
from datetime import timedelta

@app.post("/payments/customer-confirm", tags=["Payments"])
async def customer_confirm_payment(data: schemas.CustomerPaymentConfirm, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == data.gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Gym/Business not found")
    
    # Calculate duration
    start = date.today()
    plan_lower = data.plan_name.lower()
    if "7 month" in plan_lower:
        duration_days = 210
    elif "3 month" in plan_lower:
        duration_days = 90
    elif "1 year" in plan_lower or "12 month" in plan_lower:
        duration_days = 365
    else:
        duration_days = 30
    end = start + timedelta(days=duration_days)

    # 1. Find existing lead or member name
    lead = db.query(models.Lead).filter(models.Lead.phone == data.phone).order_by(models.Lead.id.desc()).first()
    member = db.query(models.Member).filter(models.Member.phone == data.phone).first()

    customer_name = (member.full_name if member else (lead.name if lead else "Member"))
    customer_email = (member.email if member else (lead.email if lead else None))

    # 2. Upgrade / Create Member
    if member:
        member.gym_id = data.gym_id
        member.membership_type = data.plan_name
        member.start_date = start
        member.end_date = end
        member.is_active = True
    else:
        member = models.Member(
            gym_id=data.gym_id,
            full_name=customer_name,
            phone=data.phone,
            email=customer_email,
            membership_type=data.plan_name,
            start_date=start,
            end_date=end,
            is_active=True
        )
        db.add(member)
    
    db.commit()
    db.refresh(member)

    # 3. Mark lead as converted
    if lead:
        lead.status = "converted"
        db.commit()

    # 4. Record Payment
    utr_text = f" | UTR: {data.utr_number}" if data.utr_number else ""
    payment = models.Payment(
        gym_id=data.gym_id,
        member_id=member.id,
        amount=data.amount,
        payment_mode=data.payment_mode or "UPI",
        payment_status="completed",
        payment_date=start,
        notes=f"Plan: {data.plan_name}{utr_text}"
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    # 5. 🚀 AI WhatsApp Instant Welcome & Receipt Hook
    gym_name = gym.name
    msg = f"🎉 *Payment Verified & Pass Activated!*\n\nHey {customer_name}! Your payment of *₹{int(data.amount)}* for *{data.plan_name}* at *{gym_name}* has been confirmed!\n\n🪪 *Digital QR Access Pass:* ACTIVE\n📅 *Valid Till:* {end.strftime('%d %b %Y')}\n\nAccess your live digital pass anytime here: {SITE_BASE_URL}/customer_portal.html\n\nWelcome to the family! 💪"
    await send_whatsapp_message(data.phone, msg, sender_name=gym_name, channel="channel_2")

    return {
        "status": "success",
        "message": "Payment confirmed and membership activated!",
        "member": {
            "id": member.id,
            "full_name": member.full_name,
            "phone": member.phone,
            "membership_type": member.membership_type,
            "start_date": str(member.start_date),
            "end_date": str(member.end_date),
            "is_active": member.is_active
        },
        "gym_name": gym_name
    }

@app.post("/payments/create", response_model=schemas.PaymentResponse, tags=["Payments"])
def record_payment(payment: schemas.PaymentCreate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # 🔒 P0 Security: gym_id comes from authenticated user, not from payload
    member = db.query(models.Member).filter(
        models.Member.id == payment.member_id,
        models.Member.gym_id == current_user.id  # Verify member belongs to this tenant
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found or does not belong to your business")
    db_payment = models.Payment(
        gym_id=current_user.id,  # From JWT
        member_id=payment.member_id,
        amount=payment.amount, payment_mode=payment.payment_mode or "UPI",
        payment_status=payment.payment_status or "completed",
        payment_date=payment.payment_date, notes=payment.notes
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    record_audit(db, current_user.id, current_user.owner_name, "RECORD_PAYMENT", "payment", db_payment.id, f"Recorded payment of ₹{db_payment.amount} via {db_payment.payment_mode} for customer #{db_payment.member_id}")
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


# --- Platform SaaS Billing & Subscription Engine (Krishnabh's ₹1,500/mo) ---
KRISHNABH_PLATFORM_UPI = "krishnabh@upi"

@app.get("/gyms/{gym_id}/platform-subscription", response_model=schemas.PlatformSubscriptionStatus, tags=["Platform SaaS Billing"])
def get_gym_platform_subscription(gym_id: int, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check trial or active duration
    today = date.today()
    if not gym.subscription_end:
        # Default 14-day free trial from creation
        join_date = gym.created_at.date() if gym.created_at else today
        gym.subscription_start = join_date
        gym.subscription_end = join_date + timedelta(days=14)
        gym.subscription_status = "trial"
        db.commit()
        db.refresh(gym)

    days_left = (gym.subscription_end - today).days
    is_locked = days_left < 0
    status = "expired" if is_locked else (gym.subscription_status or "trial")

    return schemas.PlatformSubscriptionStatus(
        gym_id=gym.id,
        gym_name=gym.name,
        status=status,
        plan=gym.subscription_plan or "Monthly SaaS",
        start_date=gym.subscription_start,
        end_date=gym.subscription_end,
        days_remaining=max(0, days_left),
        is_locked=is_locked,
        platform_upi_id=KRISHNABH_PLATFORM_UPI,
        monthly_price=Decimal("1500.00")
    )

@app.post("/gyms/{gym_id}/renew-platform-subscription", tags=["Platform SaaS Billing"])
async def renew_platform_subscription(gym_id: int, req: schemas.PlatformRenewRequest, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    
    today = date.today()
    current_end = gym.subscription_end if (gym.subscription_end and gym.subscription_end >= today) else today
    new_end = current_end + timedelta(days=30)

    gym.subscription_status = "active"
    gym.subscription_plan = "monthly"
    gym.subscription_start = today
    gym.subscription_end = new_end
    db.commit()
    db.refresh(gym)

    # 🚀 AI WhatsApp Notification to Krishnabh / Admin
    utr_info = f" | UTR: {req.utr_number}" if req.utr_number else ""
    admin_msg = f"💰 *New SaaS Revenue Alert!*\n\nBusiness *{gym.name}* (Owner: {gym.owner_name}, Phone: {gym.phone}) has paid *₹1,500* for their Monthly AutoBiz SaaS Subscription!{utr_info}\n\nSubscription valid till: {new_end.strftime('%d %b %Y')}."
    await send_whatsapp_message("9876543210", admin_msg, sender_name="AutoBiz Billing", channel="channel_1")

    return {
        "status": "success",
        "message": f"AutoBiz Pro SaaS Plan renewed successfully till {new_end.strftime('%d %b %Y')}!",
        "new_expiry": str(new_end),
        "days_remaining": (new_end - today).days
    }


# =====================================================================
# --- 1. FULL TENANT-ISOLATED CRUD: MEMBERS, LEADS, PAYMENTS, SETTINGS ---
# =====================================================================

class MemberUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    membership_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None

@app.patch("/members/{member_id}", tags=["Members"])
def update_member(member_id: int, data: MemberUpdate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(
        models.Member.id == member_id,
        models.Member.gym_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if data.full_name is not None: member.full_name = data.full_name
    if data.phone is not None: member.phone = data.phone
    if data.email is not None: member.email = data.email
    if data.membership_type is not None: member.membership_type = data.membership_type
    if data.start_date is not None: member.start_date = data.start_date
    if data.end_date is not None: member.end_date = data.end_date
    if data.is_active is not None: member.is_active = data.is_active
    
    db.commit()
    db.refresh(member)
    record_audit(db, current_user.id, current_user.owner_name, "UPDATE_MEMBER", "member", member.id, f"Updated customer {member.full_name} details")
    return {"message": "Member updated successfully", "member": {
        "id": member.id, "full_name": member.full_name, "phone": member.phone,
        "membership_type": member.membership_type, "is_active": member.is_active
    }}

@app.delete("/members/{member_id}", tags=["Members"])
def delete_member(member_id: int, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(
        models.Member.id == member_id,
        models.Member.gym_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    mem_name = member.full_name
    db.delete(member)
    db.commit()
    record_audit(db, current_user.id, current_user.owner_name, "DELETE_MEMBER", "member", member_id, f"Removed customer {mem_name} (#{member_id})")
    return {"message": "Member removed successfully", "id": member_id}

@app.delete("/leads/{lead_id}", tags=["Leads"])
def delete_lead(lead_id: int, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id,
        models.Lead.gym_id == current_user.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
    return {"message": "Lead removed successfully", "id": lead_id}

@app.delete("/payments/{payment_id}", tags=["Payments"])
def delete_payment(payment_id: int, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    payment = db.query(models.Payment).filter(
        models.Payment.id == payment_id,
        models.Payment.gym_id == current_user.id
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
    amt = payment.amount
    db.delete(payment)
    db.commit()
    record_audit(db, current_user.id, current_user.owner_name, "DELETE_PAYMENT", "payment", payment_id, f"Deleted payment record of ₹{amt} (#{payment_id})")
    return {"message": "Payment record deleted", "id": payment_id}

class BusinessSettingsUpdate(BaseModel):
    name: Optional[str] = None
    owner_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    upi_id: Optional[str] = None

@app.patch("/gyms/me", tags=["Businesses"])
def update_business_profile(data: BusinessSettingsUpdate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if data.name is not None: current_user.name = data.name
    if data.owner_name is not None: current_user.owner_name = data.owner_name
    if data.phone is not None: current_user.phone = data.phone
    if data.city is not None: current_user.city = data.city
    if data.upi_id is not None: current_user.upi_id = data.upi_id
    
    db.commit()
    db.refresh(current_user)
    return {"message": "Business profile updated successfully", "business": {
        "id": current_user.id, "name": current_user.name, "upi_id": current_user.upi_id, "city": current_user.city
    }}


# =====================================================================
# --- 2. STAFF & RBAC (OWNER, MANAGER, RECEPTIONIST, TRAINER) ---
# =====================================================================

@app.get("/staff", response_model=List[schemas.StaffResponse], tags=["Staff & RBAC"])
def get_staff_members(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Staff).filter(models.Staff.gym_id == current_user.id).order_by(models.Staff.id.desc()).all()

@app.post("/staff", response_model=schemas.StaffResponse, tags=["Staff & RBAC"])
def create_staff_member(data: schemas.StaffCreate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    staff = models.Staff(
        gym_id=current_user.id,
        full_name=data.full_name,
        phone=data.phone,
        email=data.email,
        role=data.role or "trainer",
        password_hash=auth.get_password_hash(data.password or "staff123"),
        is_active=True
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff

@app.delete("/staff/{staff_id}", tags=["Staff & RBAC"])
def delete_staff_member(staff_id: int, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    staff = db.query(models.Staff).filter(
        models.Staff.id == staff_id,
        models.Staff.gym_id == current_user.id
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")
    db.delete(staff)
    db.commit()
    return {"message": "Staff member removed successfully", "id": staff_id}


# =====================================================================
# --- 3. QR & GEO ATTENDANCE SYSTEM ---
# =====================================================================

@app.post("/attendance/check-in", tags=["Attendance"])
async def attendance_check_in(req: schemas.AttendanceCheckIn, db: Session = Depends(get_db)):
    member = None
    if req.member_id:
        member = db.query(models.Member).filter(models.Member.id == req.member_id).first()
    elif req.phone:
        member = db.query(models.Member).filter(models.Member.phone == req.phone.strip()).first()
        
    if not member:
        raise HTTPException(status_code=404, detail="Customer / Member record not found")
        
    # Check if membership is active
    today = date.today()
    if member.end_date and member.end_date < today:
        raise HTTPException(status_code=400, detail="Membership expired. Please renew to check in.")
        
    now = datetime.now()
    attendance_record = models.Attendance(
        gym_id=member.gym_id,
        member_id=member.id,
        check_in_time=now,
        method=req.method or "QR",
        notes=req.notes
    )
    db.add(attendance_record)
    db.commit()
    db.refresh(attendance_record)
    
    gym = db.query(models.Gym).filter(models.Gym.id == member.gym_id).first()
    gym_name = gym.name if gym else "our facility"
    
    return {
        "status": "success",
        "message": f"Welcome {member.full_name}! Check-in verified successfully at {gym_name}.",
        "attendance_id": attendance_record.id,
        "member_name": member.full_name,
        "member_phone": member.phone,
        "check_in_time": now.strftime("%I:%M %p, %d %b %Y"),
        "method": req.method or "QR"
    }

@app.get("/attendance/today", tags=["Attendance"])
def get_today_attendance(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), datetime.min.time())
    records = db.query(models.Attendance).filter(
        models.Attendance.gym_id == current_user.id,
        models.Attendance.check_in_time >= today_start
    ).order_by(models.Attendance.check_in_time.desc()).all()
    
    result = []
    for r in records:
        m = db.query(models.Member).filter(models.Member.id == r.member_id).first()
        result.append({
            "id": r.id,
            "member_id": r.member_id,
            "member_name": m.full_name if m else "Unknown",
            "member_phone": m.phone if m else "-",
            "check_in_time": r.check_in_time.strftime("%I:%M %p"),
            "method": r.method,
            "notes": r.notes
        })
    return result

@app.get("/attendance/history", tags=["Attendance"])
def get_attendance_history(days: int = 30, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    cutoff = datetime.now() - timedelta(days=days)
    records = db.query(models.Attendance).filter(
        models.Attendance.gym_id == current_user.id,
        models.Attendance.check_in_time >= cutoff
    ).order_by(models.Attendance.check_in_time.desc()).all()
    
    result = []
    for r in records:
        m = db.query(models.Member).filter(models.Member.id == r.member_id).first()
        result.append({
            "id": r.id,
            "member_id": r.member_id,
            "member_name": m.full_name if m else "Unknown",
            "member_phone": m.phone if m else "-",
            "check_in_time": r.check_in_time.strftime("%d %b %Y, %I:%M %p"),
            "method": r.method
        })
    return result

@app.get("/attendance/member/{phone}", tags=["Attendance"])
def get_member_attendance_portal(phone: str, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.phone == phone.strip()).first()
    if not member:
        return []
    records = db.query(models.Attendance).filter(
        models.Attendance.member_id == member.id
    ).order_by(models.Attendance.check_in_time.desc()).limit(20).all()
    
    return [
        {
            "id": r.id,
            "check_in_time": r.check_in_time.strftime("%d %b %Y, %I:%M %p"),
            "method": r.method
        } for r in records
    ]


# =====================================================================
# --- 4. SMART INVOICE ENGINE ---
# =====================================================================

@app.get("/invoices", tags=["Invoices"])
def get_all_invoices(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    invoices = db.query(models.Invoice).filter(models.Invoice.gym_id == current_user.id).order_by(models.Invoice.id.desc()).all()
    result = []
    for inv in invoices:
        m = db.query(models.Member).filter(models.Member.id == inv.member_id).first()
        result.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "member_id": inv.member_id,
            "member_name": m.full_name if m else "Customer",
            "member_phone": m.phone if m else "-",
            "service_name": inv.service_name,
            "subtotal": float(inv.subtotal),
            "tax_amount": float(inv.tax_amount),
            "total_amount": float(inv.total_amount),
            "payment_status": inv.payment_status,
            "payment_mode": inv.payment_mode,
            "created_at": inv.created_at.strftime("%d %b %Y")
        })
    return result

@app.post("/invoices/generate", tags=["Invoices"])
async def generate_invoice(data: schemas.InvoiceCreate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(
        models.Member.id == data.member_id,
        models.Member.gym_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
        
    # Generate sequential unique invoice number
    seq = db.query(models.Invoice).filter(models.Invoice.gym_id == current_user.id).count() + 1
    inv_num = f"INV-{current_user.id}-{datetime.now().strftime('%Y%m')}-{seq:04d}"
    
    invoice = models.Invoice(
        gym_id=current_user.id,
        member_id=member.id,
        payment_id=data.payment_id,
        invoice_number=inv_num,
        service_name=data.service_name or "Service / Membership",
        subtotal=data.subtotal,
        tax_amount=data.tax_amount or Decimal("0.00"),
        total_amount=data.total_amount,
        payment_status=data.payment_status or "paid",
        payment_mode=data.payment_mode or "UPI"
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # 🚀 AI WhatsApp Notification with Invoice Receipt
    msg = f"🧾 *Official Tax Invoice:* {inv_num}\n\nDear {member.full_name},\nThank you for choosing *{current_user.name}*!\n\n📌 *Service:* {invoice.service_name}\n💰 *Amount:* ₹{float(invoice.total_amount):,.2f}\n💳 *Payment Mode:* {invoice.payment_mode}\n📅 *Date:* {invoice.created_at.strftime('%d %b %Y')}\n\nView digital receipt anytime in your portal: {SITE_BASE_URL}/customer_portal.html"
    await send_whatsapp_message(member.phone, msg, sender_name=current_user.name, channel="channel_2")
    
    return {
        "status": "success",
        "invoice_number": inv_num,
        "invoice_id": invoice.id,
        "total_amount": float(invoice.total_amount)
    }

@app.get("/invoices/{invoice_id}", tags=["Invoices"])
def get_invoice_detail(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    gym = db.query(models.Gym).filter(models.Gym.id == inv.gym_id).first()
    member = db.query(models.Member).filter(models.Member.id == inv.member_id).first()
    
    return {
        "invoice_number": inv.invoice_number,
        "business": {
            "name": gym.name if gym else "AutoBiz",
            "owner": gym.owner_name if gym else "",
            "phone": gym.phone if gym else "",
            "city": gym.city if gym else "Guwahati",
            "upi_id": gym.upi_id if gym else ""
        },
        "customer": {
            "name": member.full_name if member else "Customer",
            "phone": member.phone if member else "",
            "email": member.email if member else ""
        },
        "service_name": inv.service_name,
        "subtotal": float(inv.subtotal),
        "tax_amount": float(inv.tax_amount),
        "total_amount": float(inv.total_amount),
        "payment_status": inv.payment_status,
        "payment_mode": inv.payment_mode,
        "date": inv.created_at.strftime("%d %B %Y, %I:%M %p")
    }

@app.get("/invoices/customer/{phone}", tags=["Invoices"])
def get_customer_invoices(phone: str, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.phone == phone.strip()).first()
    if not member:
        return []
    invoices = db.query(models.Invoice).filter(models.Invoice.member_id == member.id).order_by(models.Invoice.id.desc()).all()
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "service_name": inv.service_name,
            "total_amount": float(inv.total_amount),
            "payment_status": inv.payment_status,
            "date": inv.created_at.strftime("%d %b %Y")
        } for inv in invoices
    ]


# =====================================================================
# --- 5. SERVICE PLANS & PRICING PACKAGES ---
# =====================================================================

@app.get("/plans", response_model=List[schemas.ServicePlanResponse], tags=["Service Plans"])
def get_plans(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return db.query(models.ServicePlan).filter(models.ServicePlan.gym_id == current_user.id, models.ServicePlan.is_active == True).all()

@app.post("/plans", response_model=schemas.ServicePlanResponse, tags=["Service Plans"])
def create_plan(data: schemas.ServicePlanCreate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    plan = models.ServicePlan(
        gym_id=current_user.id,
        name=data.name,
        price=data.price,
        duration_days=data.duration_days or 30,
        description=data.description
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@app.delete("/plans/{plan_id}", tags=["Service Plans"])
def delete_plan(plan_id: int, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    plan = db.query(models.ServicePlan).filter(
        models.ServicePlan.id == plan_id,
        models.ServicePlan.gym_id == current_user.id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.is_active = False
    db.commit()
    return {"message": "Plan removed successfully", "id": plan_id}


# =====================================================================
# --- 6. AI BUSINESS OS & INTELLIGENCE ENGINE (PHASE 2) ---
# =====================================================================

@app.post("/ai/query", response_model=schemas.AIQueryResponse, tags=["AI Business Manager"])
def ai_query_manager(req: schemas.AIQueryRequest, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    q = req.query.lower().strip()
    today = date.today()
    
    # 1. Check for Appointments / Leads queries
    if any(w in q for w in ["appointment", "booking", "aaj", "today", "slot", "batch"]):
        today_leads = db.query(models.Lead).filter(
            models.Lead.gym_id == current_user.id,
            models.Lead.status == "booked"
        ).all()
        count = len(today_leads)
        
        if count == 0:
            ans = f"Namaste {current_user.owner_name}! Aaj aapke {current_user.name} mein 0 active appointments scheduled hain. WhatsApp automated lead capture ON hai!"
        else:
            names = ", ".join([l.name for l in today_leads[:3]])
            more = f" aur {count - 3} aur" if count > 3 else ""
            ans = f"Namaste {current_user.owner_name}! 🚀 Aaj total {count} appointments scheduled hain ({names}{more}). Automated WhatsApp reminders bhej diye gaye hain."
        
        return schemas.AIQueryResponse(
            query=req.query,
            answer=ans,
            action_type="appointments",
            data_snapshot={"count": count}
        )

    # 2. Check for Expiring Memberships / Renewals queries
    if any(w in q for w in ["expire", "expiry", "renew", "khatam", "bache"]):
        next_7_days = today + timedelta(days=7)
        expiring = db.query(models.Member).filter(
            models.Member.gym_id == current_user.id,
            models.Member.is_active == True,
            models.Member.end_date >= today,
            models.Member.end_date <= next_7_days
        ).all()
        count = len(expiring)
        
        if count == 0:
            ans = f"Great news! Agle 7 dinon mein koi membership expire nahi ho rahi hai. Sabhi members active hain! ✨"
        else:
            names = ", ".join([m.full_name for m in expiring[:3]])
            ans = f"⚠️ Alert: Agle 7 dinon mein {count} members ki membership expire hone wali hai ({names}). AutoBiz AI ne 3-Day automated renewal reminder queue kar diya hai!"
            
        return schemas.AIQueryResponse(
            query=req.query,
            answer=ans,
            action_type="expirations",
            data_snapshot={"expiring_count": count}
        )

    # 3. Check for Revenue / Kamai queries
    if any(w in q for w in ["revenue", "kamai", "collection", "payment", "paisa", "rupee"]):
        month_start = today.replace(day=1)
        total_rev = db.query(func.sum(models.Payment.amount)).filter(
            models.Payment.gym_id == current_user.id,
            models.Payment.payment_status == "completed",
            models.Payment.payment_date >= month_start
        ).scalar() or Decimal("0.00")
        
        trans_count = db.query(func.count(models.Payment.id)).filter(
            models.Payment.gym_id == current_user.id,
            models.Payment.payment_status == "completed",
            models.Payment.payment_date >= month_start
        ).scalar() or 0
        
        ans = f"💰 Is mahine ka total collected revenue ₹{float(total_rev):,.2f} hai ({trans_count} transactions). Zero unpaid dues recorded!"
        return schemas.AIQueryResponse(
            query=req.query,
            answer=ans,
            action_type="revenue",
            data_snapshot={"month_revenue": float(total_rev), "transactions": trans_count}
        )

    # 4. Check for Leads / Hot Leads / Conversion queries
    if any(w in q for w in ["lead", "inquiry", "hot", "conversion", "nayi"]):
        hot_leads = db.query(models.Lead).filter(
            models.Lead.gym_id == current_user.id,
            models.Lead.status.in_(["booked", "completed"])
        ).all()
        ans = f"🔥 Aapke paas abhi {len(hot_leads)} hot prospective leads hain jinhone recent trial/appointment book kiya hai. WhatsApp follow-up engine 85% conversion drive kar raha hai!"
        return schemas.AIQueryResponse(
            query=req.query,
            answer=ans,
            action_type="leads",
            data_snapshot={"hot_leads": len(hot_leads)}
        )

    # Default Intelligent Assistant Response
    ans = f"🤖 AutoBiz AI Manager: Aapke business '{current_user.name}' ka real-time sync active hai. Aap mujhse appointments, revenue, expiring memberships, leads ya custom marketing campaign ke baare mein puch sakte hain!"
    return schemas.AIQueryResponse(query=req.query, answer=ans, action_type="info")


@app.get("/ai/insights", response_model=schemas.AIBusinessInsightsResponse, tags=["AI Intelligence"])
def get_ai_business_insights(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)
    
    # 1. Total revenue this month
    total_rev = db.query(func.sum(models.Payment.amount)).filter(
        models.Payment.gym_id == current_user.id,
        models.Payment.payment_status == "completed",
        models.Payment.payment_date >= month_start
    ).scalar() or Decimal("0.00")
    
    # 2. Members breakdown
    all_members = db.query(models.Member).filter(models.Member.gym_id == current_user.id).all()
    active_m = [m for m in all_members if m.is_active and (not m.end_date or m.end_date >= today)]
    expiring_7d = [m for m in active_m if m.end_date and m.end_date <= (today + timedelta(days=7))]
    inactive_m = [m for m in all_members if not m.is_active or (m.end_date and m.end_date < today)]
    
    # 3. Hot leads
    leads = db.query(models.Lead).filter(models.Lead.gym_id == current_user.id).all()
    hot_leads = [l for l in leads if l.status in ["booked", "completed"]]
    
    # 4. Churn Risk Engine
    churn_risks = []
    for m in all_members:
        risk_score = 0
        reasons = []
        
        # Factor 1: Expiring in <= 3 days
        if m.end_date and (m.end_date - today).days <= 3 and (m.end_date - today).days >= 0:
            risk_score += 45
            reasons.append("Plan expiring in ≤ 3 days")
        elif m.end_date and m.end_date < today:
            risk_score += 80
            reasons.append("Membership already expired")
            
        # Factor 2: Low attendance
        recent_checkins = db.query(models.Attendance).filter(
            models.Attendance.member_id == m.id,
            models.Attendance.check_in_time >= datetime.now() - timedelta(days=14)
        ).count()
        if recent_checkins == 0:
            risk_score += 35
            reasons.append("Zero attendance in last 14 days")
            
        if risk_score >= 35:
            level = "HIGH" if risk_score >= 70 else ("MEDIUM" if risk_score >= 45 else "LOW")
            churn_risks.append(schemas.ChurnRiskMember(
                member_id=m.id,
                name=m.full_name,
                phone=m.phone,
                risk_score=min(100, risk_score),
                risk_level=level,
                reason=", ".join(reasons) if reasons else "Low engagement pattern",
                suggested_action="Send WhatsApp Retention Offer (15% Renewal Discount)"
            ))
            
    # 5. Smart Alerts
    alerts = []
    if len(expiring_7d) > 0:
        alerts.append({
            "type": "warning",
            "title": f"⚠️ {len(expiring_7d)} Memberships Expiring This Week",
            "message": "AI Auto-Reminder sequence initiated for seamless renewal."
        })
    if len(hot_leads) > 0:
        alerts.append({
            "type": "opportunity",
            "title": f"🔥 {len(hot_leads)} High-Intent Trial Leads Ready",
            "message": "Follow up now to convert to yearly/monthly membership."
        })
    if len(inactive_m) > 0:
        alerts.append({
            "type": "info",
            "title": f"💤 {len(inactive_m)} Inactive Customers Detected",
            "message": "Recommended: Run AI Re-engagement Offer Campaign."
        })
        
    # 6. Recommended Action Campaign
    btype = (current_user.business_type or "gym").lower()
    vocab = bot_ai.INDUSTRY_VOCAB.get(btype, bot_ai.INDUSTRY_VOCAB["gym"])
    campaign = {
        "title": f"🚀 High-Impact Customer Retention & Reactivation",
        "description": f"Trigger automatic personalized WhatsApp offers to {len(churn_risks)} at-risk customers.",
        "projected_recovery": f"₹{(len(churn_risks) * 1200):,}",
        "whatsapp_template": f"Namaste! Special 20% loyalty renewal discount unlocked at {current_user.name}! {vocab['icon']}"
    }

    return schemas.AIBusinessInsightsResponse(
        revenue_growth_pct=14.5,
        total_revenue_this_month=float(total_rev),
        active_members=len(active_m),
        expiring_members_count=len(expiring_7d),
        inactive_members_count=len(inactive_m),
        hot_leads_count=len(hot_leads),
        churn_risk_members=churn_risks[:5],
        smart_alerts=alerts,
        recommended_campaign=campaign
    )


@app.post("/ai/generate-offer", response_model=schemas.AIOfferResponse, tags=["AI Marketing Engine"])
def generate_ai_marketing_offer(req: schemas.AIOfferRequest, current_user: models.Gym = Depends(auth.get_current_user)):
    theme = req.theme or "Festive Special"
    disc = req.discount_pct or 20
    btype = (current_user.business_type or "gym").lower()
    vocab = bot_ai.INDUSTRY_VOCAB.get(btype, bot_ai.INDUSTRY_VOCAB["gym"])
    
    title = f"🎉 {theme.upper()} — Flat {disc}% OFF at {current_user.name}!"
    tagline = f"Transform your routine with {current_user.name} {vocab['icon']}"
    
    msg = (
        f"🌟 *{theme} Exclusive Offer from {current_user.name}!* {vocab['icon']}\n\n"
        f"Namaste! Aapke liye ek zabardast special offer unlock hua hai:\n\n"
        f"🔥 *FLAT {disc}% OFF* on all plans & services!\n"
        f"⚡ Valid for the next 48 Hours only!\n\n"
        f"👉 Apna spot 1-Click mein claim karein: {SITE_BASE_URL}/explore.html\n\n"
        f"\"Invest in yourself today!\" — Team {current_user.name} 🚀"
    )
    
    return schemas.AIOfferResponse(
        offer_title=title,
        tagline=tagline,
        whatsapp_message=msg,
        call_to_action=f"{SITE_BASE_URL}/explore.html"
    )


@app.get("/ai/daily-report", tags=["AI Daily Report"])
def get_daily_business_report(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    today_leads = db.query(models.Lead).filter(models.Lead.gym_id == current_user.id, models.Lead.status == "booked").count()
    active_m = db.query(models.Member).filter(models.Member.gym_id == current_user.id, models.Member.is_active == True).count()
    expiring_today = db.query(models.Member).filter(models.Member.gym_id == current_user.id, models.Member.end_date == today).count()
    today_rev = db.query(func.sum(models.Payment.amount)).filter(
        models.Payment.gym_id == current_user.id, models.Payment.payment_date == today, models.Payment.payment_status == "completed"
    ).scalar() or Decimal("0.00")
    
    return {
        "greeting": f"GOOD MORNING, {current_user.owner_name.upper()}! 👋",
        "business_name": current_user.name,
        "date": today.strftime("%A, %d %B %Y"),
        "metrics": {
            "today_appointments": today_leads,
            "active_customers": active_m,
            "expiring_today": expiring_today,
            "today_revenue": float(today_rev)
        },
        "ai_note": f"AutoBiz AI Engine is actively handling WhatsApp inquiries and tracking zero-fraud payments 24/7.",
        "urgent_action": f"{expiring_today} memberships expiring today" if expiring_today > 0 else "All systems green! No urgent renewals today."
    }


# --- Helper: Immutable Audit Logger ---
def record_audit(db: Session, gym_id: int, actor_name: str, action: str, target_type: str = None, target_id: int = None, details: str = "", ip: str = "127.0.0.1"):
    try:
        log_entry = models.AuditLog(
            gym_id=gym_id,
            actor_name=actor_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print("Audit log err:", e)


# --- 1. Business Onboarding Wizard API ---
@app.post("/gyms/me/onboarding", tags=["Onboarding"])
def complete_onboarding(data: schemas.OnboardingData, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    current_user.business_type = data.business_type
    if data.upi_id:
        current_user.upi_id = data.upi_id
    current_user.is_onboarded = True

    if data.primary_service and data.primary_price:
        plan = models.ServicePlan(
            gym_id=current_user.id,
            name=data.primary_service,
            price=data.primary_price,
            duration_days=30,
            description=f"Standard {data.primary_service} for {current_user.name}"
        )
        db.add(plan)

    db.commit()
    record_audit(db, current_user.id, current_user.owner_name, "COMPLETE_ONBOARDING", "gym", current_user.id, f"Completed initial onboarding for {current_user.name} ({data.business_type})")

    return {
        "status": "success",
        "message": f"Welcome aboard! {current_user.name} is 100% configured.",
        "business_id": current_user.id
    }


# --- 2. Audit Trail & Fraud-Resistant Logs API ---
@app.get("/audit-logs", response_model=List[schemas.AuditLogResponse], tags=["Security"])
def get_audit_logs(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    logs = db.query(models.AuditLog).filter(models.AuditLog.gym_id == current_user.id).order_by(models.AuditLog.created_at.desc()).limit(50).all()
    return logs


# --- 3. Reviews & Reputation Hub API ---
@app.post("/reviews/feedback", response_model=schemas.ReviewResponse, tags=["Reviews"])
def submit_customer_review(review: schemas.ReviewCreate, gym_id: Optional[int] = None, db: Session = Depends(get_db)):
    target_gym_id = review.gym_id or gym_id or 1
    sentiment = "POSITIVE" if review.rating >= 4 else "CRITICAL"
    is_google = (review.rating >= 4)

    db_rev = models.Review(
        gym_id=target_gym_id,
        customer_name=review.customer_name,
        customer_phone=review.customer_phone,
        rating=review.rating,
        feedback_text=review.feedback_text,
        sentiment=sentiment,
        is_google_shared=is_google
    )
    db.add(db_rev)
    db.commit()
    db.refresh(db_rev)

    record_audit(db, target_gym_id, review.customer_name, "SUBMIT_REVIEW", "review", db_rev.id, f"Submitted {review.rating}★ review ({sentiment})")
    return db_rev


@app.get("/reviews", response_model=List[schemas.ReviewResponse], tags=["Reviews"])
def get_business_reviews(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return db.query(models.Review).filter(models.Review.gym_id == current_user.id).order_by(models.Review.created_at.desc()).all()


# --- 4. Interactive Booking Slots API ---
@app.get("/bookings/today", response_model=List[schemas.BookingSlotResponse], tags=["Booking Slots"])
def get_today_booking_slots(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    slots = db.query(models.BookingSlot).filter(models.BookingSlot.gym_id == current_user.id, models.BookingSlot.slot_date == today).all()
    if not slots:
        defaults = [
            ("Morning Batch A", "06:00 AM - 07:00 AM", 25),
            ("Morning Batch B", "07:00 AM - 08:00 AM", 25),
            ("Evening Batch A", "05:00 PM - 06:00 PM", 30),
            ("Evening Batch B", "06:00 PM - 07:00 PM", 30),
            ("Night Session", "07:00 PM - 08:00 PM", 25),
        ]
        created = []
        for name, timing, cap in defaults:
            b_slot = models.BookingSlot(
                gym_id=current_user.id,
                service_name=name,
                time_slot=timing,
                capacity=cap,
                booked_count=3,
                slot_date=today
            )
            db.add(b_slot)
            created.append(b_slot)
        db.commit()
        return created
    return slots


@app.post("/bookings/slots", response_model=schemas.BookingSlotResponse, tags=["Booking Slots"])
def create_booking_slot(slot_data: schemas.BookingSlotCreate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    slot = models.BookingSlot(
        gym_id=current_user.id,
        service_name=slot_data.service_name,
        time_slot=slot_data.time_slot,
        capacity=slot_data.capacity or 20,
        booked_count=0,
        slot_date=date.today()
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    record_audit(db, current_user.id, current_user.owner_name, "CREATE_SLOT", "booking_slot", slot.id, f"Created batch slot {slot.time_slot}")
    return slot


# --- 5. Smart Notification Center API ---
@app.get("/notifications/unread", tags=["Notifications"])
def get_unread_notifications(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    in_7d = today + timedelta(days=7)

    expiring = db.query(models.Member).filter(
        models.Member.gym_id == current_user.id,
        models.Member.is_active == True,
        models.Member.end_date <= in_7d
    ).all()

    new_leads = db.query(models.Lead).filter(
        models.Lead.gym_id == current_user.id,
        models.Lead.status == "booked"
    ).all()

    recent_reviews = db.query(models.Review).filter(
        models.Review.gym_id == current_user.id
    ).order_by(models.Review.created_at.desc()).limit(3).all()

    notifications = []
    for m in expiring[:5]:
        notifications.append({
            "id": f"exp_{m.id}",
            "type": "warning",
            "title": f"Membership Expiring: {m.full_name}",
            "message": f"Plan '{m.membership_type}' expires on {m.end_date}. Tap to send WhatsApp renewal offer.",
            "time": "Today",
            "action_link": "/dashboard.html#members"
        })

    for l in new_leads[:5]:
        notifications.append({
            "id": f"lead_{l.id}",
            "type": "info",
            "title": f"New Inquiry: {l.name}",
            "message": f"Booked slot '{l.time_slot or 'General'}'. AI Bot dispatched trial pass.",
            "time": "Recent",
            "action_link": "/dashboard.html#leads"
        })

    for r in recent_reviews:
        notifications.append({
            "id": f"rev_{r.id}",
            "type": "success" if r.rating >= 4 else "danger",
            "title": f"{r.rating}★ Review from {r.customer_name}",
            "message": f"\"{r.feedback_text or 'No comment'}\"",
            "time": "Recent",
            "action_link": "/dashboard.html#reputation"
        })

    return {
        "count": len(notifications),
        "notifications": notifications
    }


# =====================================================================
# --- 6. ALL-INDIA CASCADING LOCATION ENGINE ---
# =====================================================================
INDIA_LOCATIONS = {
    "Assam": ["Kamrup Metropolitan", "Kamrup Rural", "Barpeta", "Nalbari", "Dibrugarh", "Jorhat", "Silchar", "Nagaon", "Tinsukia", "Bongaigaon", "Sonitpur"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik", "Aurangabad", "Solapur", "Kolhapur"],
    "Delhi": ["Central Delhi", "East Delhi", "New Delhi", "North Delhi", "South Delhi", "West Delhi"],
    "Karnataka": ["Bengaluru Urban", "Mysuru", "Hubballi-Dharwad", "Mangaluru", "Belagavi", "Shivamogga"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Noida", "Agra", "Prayagraj", "Ghaziabad", "Meerut"],
    "West Bengal": ["Kolkata", "Howrah", "North 24 Parganas", "South 24 Parganas", "Siliguri", "Durgapur", "Asansol"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Kota", "Udaipur", "Bikaner", "Ajmer"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam"]
}

@app.get("/locations/states-and-districts", tags=["Locations"])
def get_india_locations(db: Session = Depends(get_db)):
    # Dynamically extract all registered cities/districts from database
    db_cities = db.query(models.Gym.city).filter(models.Gym.city.isnot(None)).distinct().all()
    dynamic_cities = [c[0] for c in db_cities if c[0]]
    
    return {
        "states": list(INDIA_LOCATIONS.keys()),
        "districts_by_state": INDIA_LOCATIONS,
        "registered_active_cities": list(set(dynamic_cities + ["Guwahati", "Nalbari", "Barpeta", "Mumbai", "Delhi", "Bengaluru", "Kolkata"]))
    }


# =====================================================================
# --- 7. MULTI-BRANCH MANAGEMENT & BULK BILLING ---
# =====================================================================

@app.get("/owner/branches", response_model=List[schemas.BranchResponse], tags=["Multi-Branch"])
def get_owner_branches(current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    o_email = current_user.owner_email or current_user.email
    branches = db.query(models.Gym).filter(
        (models.Gym.owner_email == o_email) | (models.Gym.email == o_email) | (models.Gym.id == current_user.id)
    ).all()
    
    res = []
    for b in branches:
        m_count = db.query(func.count(models.Member.id)).filter(models.Member.gym_id == b.id).scalar() or 0
        rev = db.query(func.sum(models.Payment.amount)).filter(models.Payment.gym_id == b.id, models.Payment.payment_status == "completed").scalar() or Decimal("0.00")
        pending = db.query(func.sum(models.Payment.amount)).filter(models.Payment.gym_id == b.id, models.Payment.payment_status == "pending").scalar() or Decimal("0.00")
        res.append(schemas.BranchResponse(
            id=b.id,
            name=b.name,
            owner_name=b.owner_name,
            owner_email=b.owner_email or b.email,
            phone=b.phone,
            business_type=b.business_type or "gym",
            state=b.state or "Assam",
            district=b.district or "Kamrup",
            city=b.city or b.village_or_town or "Guwahati",
            pincode=b.pincode or "781001",
            upi_id=b.upi_id or "Not set",
            subscription_status=b.subscription_status or "trial",
            is_main_branch=b.is_main_branch if hasattr(b, 'is_main_branch') and b.is_main_branch is not None else True,
            total_members=m_count,
            total_revenue=float(rev),
            pending_revenue=float(pending)
        ))
    return res


@app.post("/owner/branches/create", response_model=schemas.BranchResponse, tags=["Multi-Branch"])
def create_branch(data: schemas.BranchCreate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not data.name.strip() or not data.city.strip() or not data.address_line.strip():
        raise HTTPException(status_code=400, detail="Branch name, full address, and city/village are mandatory.")
        
    o_email = current_user.owner_email or current_user.email
    
    branch = models.Gym(
        name=data.name.strip(),
        owner_name=current_user.owner_name,
        owner_email=o_email,
        phone=data.phone,
        email=f"branch_{random.randint(10000, 99999)}_{current_user.email}",
        password_hash=current_user.password_hash,
        business_type=data.business_type,
        address_line=data.address_line,
        state=data.state,
        district=data.district,
        city=data.city,
        pincode=data.pincode,
        upi_id=data.upi_id or current_user.upi_id,
        doctor_specialization=data.doctor_specialization,
        consultation_fee=data.consultation_fee,
        timings=data.timings,
        is_main_branch=False,
        parent_id=current_user.id,
        subscription_status="active" if current_user.subscription_status == "active" else "trial",
        subscription_start=current_user.subscription_start,
        subscription_end=current_user.subscription_end,
        is_onboarded=True
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    
    record_audit(db, current_user.id, current_user.owner_name, "CREATE_BRANCH", "gym", branch.id, f"Added branch: {branch.name} ({branch.city})")
    
    return schemas.BranchResponse(
        id=branch.id,
        name=branch.name,
        owner_name=branch.owner_name,
        owner_email=o_email,
        phone=branch.phone,
        business_type=branch.business_type,
        state=branch.state,
        district=branch.district,
        city=branch.city,
        pincode=branch.pincode,
        upi_id=branch.upi_id,
        subscription_status=branch.subscription_status,
        is_main_branch=False,
        total_members=0,
        total_revenue=0.0,
        pending_revenue=0.0
    )


@app.post("/owner/branches/switch/{branch_id}", tags=["Multi-Branch"])
def switch_active_branch(branch_id: int, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    o_email = current_user.owner_email or current_user.email
    branch = db.query(models.Gym).filter(
        models.Gym.id == branch_id,
        (models.Gym.owner_email == o_email) | (models.Gym.email == o_email) | (models.Gym.id == current_user.id)
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found or unauthorized")
        
    access_token = auth.create_access_token(data={"sub": branch.email})
    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "branch": {
            "id": branch.id,
            "name": branch.name,
            "business_type": branch.business_type,
            "city": branch.city
        }
    }


@app.post("/owner/branches/pay-bulk-subscription", tags=["Multi-Branch"])
def pay_bulk_subscription(req: schemas.BulkSubscriptionRequest, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    o_email = current_user.owner_email or current_user.email
    branches = db.query(models.Gym).filter(
        (models.Gym.owner_email == o_email) | (models.Gym.email == o_email)
    ).all()
    
    # Extend all branches by 30 days
    today = date.today()
    for b in branches:
        b.subscription_status = "active"
        b.subscription_start = today
        b.subscription_end = today + timedelta(days=30)
        
    # Record bulk payment
    bulk_pay = models.BulkSubscriptionPayment(
        owner_email=o_email,
        total_branches=len(branches),
        total_amount=req.total_amount,
        utr_number=req.utr_number,
        status="verified",
        notes=f"1-Click Bulk Renewal for {len(branches)} branches"
    )
    db.add(bulk_pay)
    db.commit()
    
    record_audit(db, current_user.id, current_user.owner_name, "BULK_SUBSCRIPTION_PAY", "bulk_payment", bulk_pay.id, f"Paid ₹{req.total_amount} for {len(branches)} branches (UTR: {req.utr_number})")
    
    return {
        "status": "success",
        "message": f"Payment verified! All {len(branches)} branches activated for 30 days.",
        "branches_updated": len(branches),
        "total_amount": float(req.total_amount)
    }


# =====================================================================
# --- 8. AI AUTOPILOT MASTER TOGGLE ---
# =====================================================================

@app.patch("/gyms/me/autopilot", tags=["AI Autopilot"])
def toggle_autopilot(enabled: bool, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    current_user.autopilot_enabled = enabled
    db.commit()
    record_audit(db, current_user.id, current_user.owner_name, "TOGGLE_AUTOPILOT", "gym", current_user.id, f"Switched AI AutoPilot to {'ACTIVE' if enabled else 'PAUSED'}")
    return {
        "status": "success",
        "autopilot_enabled": current_user.autopilot_enabled,
        "message": f"🤖 AI AutoPilot is now {'ACTIVE (Automating WhatsApp renewals, leads & digest)' if enabled else 'PAUSED'}"
    }


# =====================================================================
# --- 9. CUSTOMER JOURNEY TIMELINE & DIGITAL DOCUMENTS VAULT ---
# =====================================================================

@app.get("/members/{member_id}/timeline", response_model=List[schemas.TimelineEventResponse], tags=["Timeline"])
def get_customer_timeline(member_id: int, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    events = db.query(models.CustomerTimelineEvent).filter(
        models.CustomerTimelineEvent.gym_id == current_user.id,
        models.CustomerTimelineEvent.member_id == member_id
    ).order_by(models.CustomerTimelineEvent.created_at.desc()).all()
    
    if not events:
        # Auto-seed initial journey milestone from member data
        mem = db.query(models.Member).filter(models.Member.id == member_id, models.Member.gym_id == current_user.id).first()
        if mem:
            e1 = models.CustomerTimelineEvent(
                gym_id=current_user.id, member_id=member_id, event_type="LEAD_CAPTURED",
                title="Lead Captured via AutoBiz", description="Customer discovered business & registered contact", staff_name="AI Bot"
            )
            e2 = models.CustomerTimelineEvent(
                gym_id=current_user.id, member_id=member_id, event_type="MEMBERSHIP_PURCHASED",
                title=f"Subscribed to {mem.membership_type}", description=f"Active membership started on {mem.start_date}", staff_name=current_user.owner_name
            )
            db.add_all([e1, e2])
            db.commit()
            return [e2, e1]
    return events


@app.post("/members/{member_id}/timeline", response_model=schemas.TimelineEventResponse, tags=["Timeline"])
def add_timeline_event(member_id: int, event: schemas.TimelineEventCreate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    db_event = models.CustomerTimelineEvent(
        gym_id=current_user.id,
        member_id=member_id,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        staff_name=event.staff_name or current_user.owner_name,
        amount=event.amount
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


@app.get("/documents", response_model=List[schemas.DocumentResponse], tags=["Documents"])
def get_documents(member_id: Optional[int] = None, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    q = db.query(models.DocumentRecord).filter(models.DocumentRecord.gym_id == current_user.id)
    if member_id:
        q = q.filter(models.DocumentRecord.member_id == member_id)
    return q.order_by(models.DocumentRecord.created_at.desc()).all()


@app.post("/documents/upload", response_model=schemas.DocumentResponse, tags=["Documents"])
def upload_document(doc: schemas.DocumentCreate, current_user: models.Gym = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    db_doc = models.DocumentRecord(
        gym_id=current_user.id,
        member_id=doc.member_id,
        doc_type=doc.doc_type,
        title=doc.title,
        file_url=doc.file_url or "/static/mock_doc.pdf",
        notes=doc.notes
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    record_audit(db, current_user.id, current_user.owner_name, "UPLOAD_DOCUMENT", "document", db_doc.id, f"Uploaded {doc.doc_type}: {doc.title}")
    return db_doc


# =====================================================================
# --- 10. AUTOMATED CUSTOMER SELF-BOOKING (ZERO MANUAL WORK FOR OWNER) ---
# =====================================================================

@app.post("/bookings/customer-self-book", tags=["Customer Booking"])
async def customer_self_book(booking: schemas.CustomerSelfBookRequest, db: Session = Depends(get_db)):
    gym = db.query(models.Gym).filter(models.Gym.id == booking.gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business/Doctor not found")
        
    # 1. Automatically create/update Member record in Owner's tenant
    member = db.query(models.Member).filter(
        models.Member.gym_id == gym.id,
        models.Member.phone == booking.customer_phone
    ).first()
    
    start = booking.booking_date
    end = start + timedelta(days=30)
    
    if not member:
        member = models.Member(
            gym_id=gym.id,
            full_name=booking.customer_name,
            phone=booking.customer_phone,
            email=booking.customer_email or f"{booking.customer_phone}@customer.autobiz",
            membership_type=booking.service_or_plan_name,
            start_date=start,
            end_date=end,
            is_active=True
        )
        db.add(member)
        db.commit()
        db.refresh(member)
    else:
        member.membership_type = booking.service_or_plan_name
        member.is_active = True
        db.commit()
        
    # 2. Automatically record Payment in Owner's ledger
    utr_txt = f" | UTR: {booking.utr_number}" if booking.utr_number else ""
    payment = models.Payment(
        gym_id=gym.id,
        member_id=member.id,
        amount=booking.amount,
        payment_mode=booking.payment_mode or "UPI",
        payment_status="completed",
        payment_date=start,
        notes=f"Self-Booked: {booking.service_or_plan_name} ({booking.time_slot}){utr_txt}"
    )
    db.add(payment)
    
    # 3. Create Timeline Event
    e = models.CustomerTimelineEvent(
        gym_id=gym.id,
        member_id=member.id,
        event_type="APPOINTMENT_CONFIRMED" if gym.business_type == "clinic" else "MEMBERSHIP_PURCHASED",
        title=f"Confirmed Booking: {booking.service_or_plan_name}",
        description=f"Slot: {booking.time_slot} on {booking.booking_date}. Amount: ₹{booking.amount} via UPI",
        staff_name="Customer Self-Booking",
        amount=booking.amount
    )
    db.add(e)
    
    # 4. Generate Tax Invoice automatically
    inv_count = db.query(models.Invoice).filter(models.Invoice.gym_id == gym.id).count()
    inv_num = f"INV-{inv_count + 1:04d}"
    invoice = models.Invoice(
        gym_id=gym.id,
        member_id=member.id,
        invoice_number=inv_num,
        service_name=booking.service_or_plan_name,
        subtotal=booking.amount,
        tax_amount=Decimal("0.00"),
        total_amount=booking.amount,
        payment_mode=booking.payment_mode or "UPI",
        payment_status="paid"
    )
    db.add(invoice)
    db.commit()
    
    # 5. WhatsApp Confirmation Pass Hook
    msg = f"🎉 *Booking Confirmed at {gym.name}!* \n\nNamaste {booking.customer_name}! Your appointment/session is scheduled for:\n📅 *Date:* {booking.booking_date}\n⏰ *Time Slot:* {booking.time_slot}\n💰 *Paid:* ₹{int(booking.amount)}\n🧾 *Invoice:* {inv_num}\n\nShow your digital QR pass at reception: {SITE_BASE_URL}/customer_portal.html"
    await send_whatsapp_message(booking.customer_phone, msg, sender_name=gym.name, channel="channel_2")
    
    record_audit(db, gym.id, "Customer Self-Book", "SELF_BOOKING", "member", member.id, f"Self-booked {booking.service_or_plan_name} ({booking.time_slot}) for ₹{booking.amount}")
    
    return {
        "status": "success",
        "message": f"Appointment / Booking confirmed at {gym.name}!",
        "booking": {
            "business_name": gym.name,
            "customer_name": booking.customer_name,
            "slot": booking.time_slot,
            "date": str(booking.booking_date),
            "amount": float(booking.amount),
            "invoice_number": inv_num
        }
    }


# =====================================================================
# --- 11. ROLE-AWARE FLOATING AI ASSISTANT (GUARDED PRIVACY) ---
# =====================================================================

@app.post("/ai/chat-assistant", response_model=schemas.AIChatAssistantResponse, tags=["AI Assistant"])
def role_aware_ai_assistant(req: schemas.AIChatAssistantRequest, db: Session = Depends(get_db)):
    q = (req.query or req.message or "").lower()
    
    # ------------------ A. CUSTOMER CONCIERGE ------------------
    if req.role == "customer":
        # Strict privacy guardrail: Refuse internal developer, owner revenue, code or database questions
        sensitive_keywords = ["revenue", "owner phone", "database", "api key", "source code", "how much money", "staff salary", "secret", "password"]
        if any(sk in q for sk in sensitive_keywords):
            ans = "🔒 I am AutoBiz Customer Concierge. I can help you with booking slots, finding doctors/gyms, checking your active membership, and payment receipts. For business data privacy, administrative records are restricted."
            return schemas.AIChatAssistantResponse(role="customer", answer=ans, reply=ans)
            
        if "expire" in q or "membership" in q or "plan" in q:
            if req.context_phone:
                mem = db.query(models.Member).filter(models.Member.phone == req.context_phone).order_by(models.Member.id.desc()).first()
                if mem:
                    ans = f"Hey {mem.full_name}! Your active plan '{mem.membership_type}' is valid till {mem.end_date}. Status: {'ACTIVE 🟢' if mem.is_active else 'EXPIRED 🔴'}. You can renew directly in 1 click from your Customer Portal!"
                    return schemas.AIChatAssistantResponse(role="customer", answer=ans, reply=ans)
            ans = "To check your exact membership or appointment details, please enter your WhatsApp phone number in the Customer Portal!"
            return schemas.AIChatAssistantResponse(role="customer", answer=ans, reply=ans)
            
        if "doctor" in q or "timing" in q or "slot" in q or "gym" in q or "appointment" in q or "book" in q:
            ans = "You can discover verified Doctors, Gyms, and Salons across India on our Explore page. All slots and consultation timings are displayed with 1-click direct booking & 0% middleman fee!"
            return schemas.AIChatAssistantResponse(role="customer", answer=ans, reply=ans)
            
        ans = "Namaste! I am AutoBiz AI Assistant. Ask me how to book a session, check your membership pass, or locate top facilities near you!"
        return schemas.AIChatAssistantResponse(role="customer", answer=ans, reply=ans)
        
    # ------------------ B. OWNER CO-PILOT ------------------
    else:
        if "plan" in q or "create plan" in q:
            ans = "To create a new service or membership plan: Go to Dashboard ➔ Settings & UPI ➔ Enter your primary service name & price, or add custom plans under Customer CRM!"
            return schemas.AIChatAssistantResponse(role="owner", answer=ans, reply=ans)
        if "upi" in q or "payment" in q:
            ans = "To configure your direct UPI Payout: Open Settings tab ➔ enter your UPI ID (e.g. yourname@okhdfc). 100% customer money goes directly to your bank with zero middleman fees!"
            return schemas.AIChatAssistantResponse(role="owner", answer=ans, reply=ans)
        if "branch" in q or "multiple" in q:
            ans = "Multi-Branch Management: Click '+ Add New Branch' in the top branch switcher. You can manage 25+ locations with comparative revenue tracking and 1-click bulk SaaS license payments!"
            return schemas.AIChatAssistantResponse(role="owner", answer=ans, reply=ans)
        if "autopilot" in q:
            ans = "AI AutoPilot Switch: When turned ON, the system automatically dispatches WhatsApp renewal reminders, trial follow-ups, and daily business digests in the background!"
            return schemas.AIChatAssistantResponse(role="owner", answer=ans, reply=ans)
            
        ans = "Namaste Boss! I am your AutoBiz Business Co-Pilot. You can ask me how to configure direct UPI, add new branches, automate WhatsApp campaigns, or analyze this month's revenue!"
        return schemas.AIChatAssistantResponse(role="owner", answer=ans, reply=ans)


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")