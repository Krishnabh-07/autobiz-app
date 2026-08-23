"""
whatsapp_routes.py — WhatsApp Automation, AI Message Generation & 3-Day Expiry Engine
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from typing import Optional, List
import models
import bot_ai
from database import get_db

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp AI Automation"])

# In-memory message dispatch log for real-time audit
DISPATCH_LOGS = []


@router.get("/generate/trial-followup")
def generate_trial_followup(
    gym_id: int,
    customer_name: str,
    phone: str,
    db: Session = Depends(get_db)
):
    gym = db.query(models.Gym).filter(models.Gym.id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    
    msg = bot_ai.get_trial_followup_message(
        customer_name=customer_name,
        business_name=gym.name,
        business_type=gym.business_type or "gym"
    )
    
    clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
        
    import urllib.parse
    wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
    
    return {
        "customer_name": customer_name,
        "phone": phone,
        "business_name": gym.name,
        "message": msg,
        "whatsapp_url": wa_url
    }


@router.get("/generate/customer-reminder")
def generate_customer_reminder(
    member_id: int,
    days_left: int = 3,
    db: Session = Depends(get_db)
):
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    gym = member.gym
    msg = bot_ai.get_customer_expiry_reminder(
        customer_name=member.full_name,
        business_name=gym.name if gym else "Our Club",
        business_type=gym.business_type if gym else "gym",
        days_left=days_left
    )
    
    clean_phone = member.phone.replace("+", "").replace("-", "").replace(" ", "")
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
        
    import urllib.parse
    wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
    
    return {
        "member_id": member.id,
        "member_name": member.full_name,
        "phone": member.phone,
        "end_date": str(member.end_date),
        "days_left": days_left,
        "message": msg,
        "whatsapp_url": wa_url
    }


@router.get("/generate/owner-reminder")
def generate_owner_reminder(
    gym_id: int,
    days_left: int = 3,
    db: Session = Depends(get_db)
):
    gym = db.query(models.Gym).filter(models.Gym.id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")
    
    msg = bot_ai.get_owner_subscription_reminder(
        owner_name=gym.owner_name,
        business_name=gym.name,
        days_left=days_left
    )
    
    clean_phone = gym.phone.replace("+", "").replace("-", "").replace(" ", "")
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
        
    import urllib.parse
    wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
    
    return {
        "gym_id": gym.id,
        "owner_name": gym.owner_name,
        "phone": gym.phone,
        "subscription_end": str(gym.subscription_end),
        "days_left": days_left,
        "message": msg,
        "whatsapp_url": wa_url
    }


@router.get("/scan-due-reminders")
def scan_due_reminders(db: Session = Depends(get_db)):
    """
    Automated Scan Engine:
    Finds:
    1. Members whose plan expires in 3 days (or today/tomorrow)
    2. Business owners whose subscription expires in 3 days
    Generates personalized meme reminders and creates a ready dispatch queue.
    """
    today = date.today()
    three_days_later = today + timedelta(days=3)
    
    # 1. Check Members expiring soon
    expiring_members = db.query(models.Member).filter(
        models.Member.end_date.between(today, three_days_later),
        models.Member.is_active == True
    ).all()
    
    member_reminders = []
    for m in expiring_members:
        days_left = (m.end_date - today).days if m.end_date else 0
        gym = m.gym
        msg = bot_ai.get_customer_expiry_reminder(
            customer_name=m.full_name,
            business_name=gym.name if gym else "Our Fitness Club",
            business_type=gym.business_type if gym else "gym",
            days_left=max(days_left, 1)
        )
        clean_phone = m.phone.replace("+", "").replace("-", "").replace(" ", "")
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone
        import urllib.parse
        wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
        
        member_reminders.append({
            "type": "customer_membership_expiry",
            "name": m.full_name,
            "phone": m.phone,
            "business": gym.name if gym else "Club",
            "end_date": str(m.end_date),
            "days_left": days_left,
            "message": msg,
            "whatsapp_url": wa_url
        })

    # 2. Check Business Owners expiring soon
    expiring_owners = db.query(models.Gym).filter(
        models.Gym.subscription_end.between(today, three_days_later)
    ).all()
    
    owner_reminders = []
    for g in expiring_owners:
        days_left = (g.subscription_end - today).days if g.subscription_end else 0
        msg = bot_ai.get_owner_subscription_reminder(
            owner_name=g.owner_name,
            business_name=g.name,
            days_left=max(days_left, 1)
        )
        clean_phone = g.phone.replace("+", "").replace("-", "").replace(" ", "")
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone
        import urllib.parse
        wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"
        
        owner_reminders.append({
            "type": "owner_subscription_expiry",
            "owner_name": g.owner_name,
            "business_name": g.name,
            "phone": g.phone,
            "subscription_end": str(g.subscription_end),
            "days_left": days_left,
            "message": msg,
            "whatsapp_url": wa_url
        })
        
    return {
        "scanned_at": str(today),
        "total_member_reminders": len(member_reminders),
        "total_owner_reminders": len(owner_reminders),
        "member_reminders": member_reminders,
        "owner_reminders": owner_reminders
    }


@router.post("/trigger-automation-now")
def trigger_automation_now():
    """Immediately runs background Channel 1 & Channel 2 automated AI dispatch."""
    import scheduler
    return scheduler.trigger_all_automations_now()


@router.get("/dispatch-history")
def get_dispatch_history(channel: Optional[str] = None):
    """Returns the live audit log of automated WhatsApp dispatches."""
    import whatsapp_cloud
    return whatsapp_cloud.get_dispatch_history(channel=channel, limit=30)

