# backend/admin.py — Super Admin God Mode APIs
# Only Krishnabh can access these routes via secret key header

import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal
import models
from database import get_db

router = APIRouter(prefix="/superadmin", tags=["Super Admin God Mode"])

# --- Super Admin Secret Key (Change this in production!) ---
SUPER_ADMIN_KEY = "krishnabh_god_mode_2024_secret"
PLATFORM_FEE_PER_MONTH = 1500  # Rs per business per month


def verify_admin(x_admin_key: str = Header(None)):
    if x_admin_key != SUPER_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Access Denied. Invalid Super Admin Key.")
    return True


# --- 1. Platform Overview ---
@router.get("/overview")
def get_platform_overview(db: Session = Depends(get_db), _=Depends(verify_admin)):
    total_businesses = db.query(func.count(models.Gym.id)).scalar() or 0
    total_members = db.query(func.count(models.Member.id)).scalar() or 0
    total_leads = db.query(func.count(models.Lead.id)).scalar() or 0
    total_revenue_collected = db.query(func.sum(models.Payment.amount)).filter(
        models.Payment.payment_status == "completed"
    ).scalar() or Decimal("0.00")

    # Subscription counts
    active_subs = db.query(func.count(models.Gym.id)).filter(
        models.Gym.subscription_status == "active"
    ).scalar() or 0
    trial_subs = db.query(func.count(models.Gym.id)).filter(
        models.Gym.subscription_status == "trial"
    ).scalar() or 0
    expired_subs = db.query(func.count(models.Gym.id)).filter(
        models.Gym.subscription_status == "expired"
    ).scalar() or 0

    # Business type breakdown
    type_breakdown = db.query(
        models.Gym.business_type,
        func.count(models.Gym.id).label("count")
    ).group_by(models.Gym.business_type).all()

    # Platform monthly income (active subscriptions only)
    platform_income = active_subs * PLATFORM_FEE_PER_MONTH

    return {
        "total_businesses": total_businesses,
        "total_members": total_members,
        "total_leads": total_leads,
        "total_revenue_on_platform": float(total_revenue_collected),
        "platform_monthly_income": platform_income,
        "platform_income_label": f"Rs {platform_income:,}/month",
        "subscription_summary": {
            "active": active_subs,
            "trial": trial_subs,
            "expired": expired_subs,
            "defaulters": expired_subs + trial_subs
        },
        "business_type_breakdown": [
            {"type": row.business_type, "count": row.count}
            for row in type_breakdown
        ]
    }


# --- 2. All Businesses with Deep Data ---
@router.get("/businesses")
def get_all_businesses_admin(db: Session = Depends(get_db), _=Depends(verify_admin)):
    gyms = db.query(models.Gym).all()
    result = []
    for gym in gyms:
        member_count = db.query(func.count(models.Member.id)).filter(
            models.Member.gym_id == gym.id
        ).scalar() or 0
        lead_count = db.query(func.count(models.Lead.id)).filter(
            models.Lead.gym_id == gym.id
        ).scalar() or 0
        revenue = db.query(func.sum(models.Payment.amount)).filter(
            models.Payment.gym_id == gym.id,
            models.Payment.payment_status == "completed"
        ).scalar() or Decimal("0.00")

        result.append({
            "id": gym.id,
            "business_name": gym.name,
            "owner_name": gym.owner_name,
            "phone": gym.phone,
            "email": gym.email,
            "business_type": gym.business_type or "gym",
            "city": gym.city or "N/A",
            "upi_id": gym.upi_id or "Not Set",
            "member_count": member_count,
            "lead_count": lead_count,
            "revenue_collected": float(revenue),
            "subscription_status": gym.subscription_status or "trial",
            "subscription_plan": gym.subscription_plan or "monthly",
            "subscription_end": str(gym.subscription_end) if gym.subscription_end else "Not Set",
            "joined_on": str(gym.created_at.date()) if gym.created_at else "N/A",
        })
    return result


# --- 3. Subscription Defaulters ---
@router.get("/defaulters")
def get_defaulters(db: Session = Depends(get_db), _=Depends(verify_admin)):
    defaulters = db.query(models.Gym).filter(
        models.Gym.subscription_status.in_(["expired", "trial"])
    ).all()
    return [
        {
            "id": g.id,
            "business_name": g.name,
            "owner_name": g.owner_name,
            "phone": g.phone,
            "email": g.email,
            "city": g.city or "N/A",
            "status": g.subscription_status,
            "subscription_end": str(g.subscription_end) if g.subscription_end else "Never Paid"
        }
        for g in defaulters
    ]


# --- 4. Update Subscription Status (After Payment) ---
@router.patch("/businesses/{gym_id}/subscription")
def update_subscription(
    gym_id: int,
    status: str,
    plan: str = "monthly",
    db: Session = Depends(get_db),
    _=Depends(verify_admin)
):
    gym = db.query(models.Gym).filter(models.Gym.id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Business not found")

    from datetime import date, timedelta
    plan_days = {"monthly": 30, "quarterly": 90, "yearly": 365}
    days = plan_days.get(plan, 30)

    gym.subscription_status = status
    gym.subscription_plan = plan
    gym.subscription_start = date.today()
    gym.subscription_end = date.today() + timedelta(days=days)
    db.commit()
    db.refresh(gym)
    return {"message": f"Subscription updated to {status} ({plan})", "gym_id": gym_id}


# --- 5. Platform Income Summary ---
@router.get("/income")
def get_platform_income(db: Session = Depends(get_db), _=Depends(verify_admin)):
    active = db.query(func.count(models.Gym.id)).filter(
        models.Gym.subscription_status == "active"
    ).scalar() or 0
    monthly = db.query(func.count(models.Gym.id)).filter(
        models.Gym.subscription_status == "active",
        models.Gym.subscription_plan == "monthly"
    ).scalar() or 0
    quarterly = db.query(func.count(models.Gym.id)).filter(
        models.Gym.subscription_status == "active",
        models.Gym.subscription_plan == "quarterly"
    ).scalar() or 0
    yearly = db.query(func.count(models.Gym.id)).filter(
        models.Gym.subscription_status == "active",
        models.Gym.subscription_plan == "yearly"
    ).scalar() or 0

    return {
        "active_paying_businesses": active,
        "plan_breakdown": {
            "monthly": monthly,
            "quarterly": quarterly,
            "yearly": yearly
        },
        "monthly_income": active * PLATFORM_FEE_PER_MONTH,
        "yearly_projected": active * PLATFORM_FEE_PER_MONTH * 12,
        "income_milestones": {
            "10_businesses": 10 * PLATFORM_FEE_PER_MONTH,
            "50_businesses": 50 * PLATFORM_FEE_PER_MONTH,
            "100_businesses": 100 * PLATFORM_FEE_PER_MONTH,
            "500_businesses": 500 * PLATFORM_FEE_PER_MONTH
        }
    }