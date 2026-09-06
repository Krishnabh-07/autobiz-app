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

# --- Super Admin Secret Key (Set SUPER_ADMIN_KEY env var in production!) ---
SUPER_ADMIN_KEY = os.environ.get("SUPER_ADMIN_KEY", "krishnabh_god_mode_2024_secret")
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

    # Payment status breakdown (registration payments)
    payments_verified = db.query(func.count(models.Gym.id)).filter(
        models.Gym.payment_status == "verified"
    ).scalar() or 0
    payments_pending = db.query(func.count(models.Gym.id)).filter(
        (models.Gym.payment_status == "pending") | (models.Gym.subscription_status == "awaiting_payment")
    ).scalar() or 0
    total_collected_platform = db.query(func.sum(models.Gym.payment_amount)).filter(
        models.Gym.payment_status == "verified"
    ).scalar() or Decimal("0.00")

    return {
        "total_businesses": total_businesses,
        "total_members": total_members,
        "total_leads": total_leads,
        "total_revenue_on_platform": float(total_revenue_collected),
        "platform_monthly_income": platform_income,
        "platform_income_label": f"Rs {platform_income:,}/month",
        "platform_payments_collected": float(total_collected_platform),
        "payment_breakdown": {
            "verified": payments_verified,
            "pending": payments_pending,
            "total_collected": float(total_collected_platform)
        },
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
            "selected_plan": gym.selected_plan or gym.subscription_plan or "monthly",
            "payment_status": gym.payment_status or "pending",
            "payment_amount": float(gym.payment_amount) if gym.payment_amount else None,
            "payment_date": str(gym.payment_date) if gym.payment_date else None,
            "payment_utr": gym.payment_utr or None,
            "transaction_id": gym.transaction_id or None,
            "subscription_start": str(gym.subscription_start) if gym.subscription_start else None,
            "subscription_end": str(gym.subscription_end) if gym.subscription_end else "Not Set",
            "joined_on": str(gym.created_at.date()) if gym.created_at else "N/A",
        })
    return result


# --- 2b. All Owner Payments (God Mode Billing Ledger) ---
@router.get("/payments-ledger")
def get_god_mode_payments_ledger(db: Session = Depends(get_db), _=Depends(verify_admin)):
    """Platform billing ledger — every registration/renewal payment with plan, status, amount, UTR."""
    gyms = db.query(models.Gym).all()
    ledger = []
    for g in gyms:
        if not (g.payment_status and g.payment_status != "pending"):
            continue
        ledger.append({
            "gym_id": g.id,
            "business_name": g.name,
            "owner_name": g.owner_name,
            "owner_email": g.owner_email or g.email,
            "phone": g.phone,
            "selected_plan": g.selected_plan or g.subscription_plan or "monthly",
            "payment_status": g.payment_status,
            "amount": float(g.payment_amount) if g.payment_amount else 0.0,
            "payment_mode": g.payment_mode or "UPI",
            "payment_date": str(g.payment_date) if g.payment_date else None,
            "utr_number": g.payment_utr or None,
            "transaction_id": g.transaction_id or None,
            "subscription_start": str(g.subscription_start) if g.subscription_start else None,
            "subscription_end": str(g.subscription_end) if g.subscription_end else None,
            "branch_count": db.query(func.count(models.Gym.id)).filter(
                (models.Gym.owner_email == (g.owner_email or g.email)) | (models.Gym.email == (g.owner_email or g.email))
            ).scalar() or 1
        })
    ledger.sort(key=lambda x: x["payment_date"] or "", reverse=True)
    return ledger


# --- 2c. Pending Payments (Owners awaiting verification) ---
@router.get("/pending-payments")
def get_pending_owner_payments(db: Session = Depends(get_db), _=Depends(verify_admin)):
    pending = db.query(models.Gym).filter(
        (models.Gym.payment_status == "pending") | (models.Gym.subscription_status == "awaiting_payment")
    ).all()
    return [
        {
            "gym_id": g.id,
            "business_name": g.name,
            "owner_name": g.owner_name,
            "phone": g.phone,
            "email": g.email,
            "selected_plan": g.selected_plan or "monthly",
            "amount": float(g.payment_amount) if g.payment_amount else 1500.0,
            "subscription_status": g.subscription_status,
            "created_at": str(g.created_at.date()) if g.created_at else "N/A"
        }
        for g in pending
    ]


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
    gym.selected_plan = gym.selected_plan or plan
    gym.subscription_start = date.today()
    gym.subscription_end = date.today() + timedelta(days=days)
    if status == "active" and gym.payment_status != "verified":
        gym.payment_status = "verified"
        gym.payment_amount = gym.payment_amount or (Decimal("1500.00") if plan == "monthly" else Decimal("4000.00"))
        gym.payment_date = date.today()
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


# --- 6. GOD MODE: Owners Multi-Branch Portfolio View ---
@router.get("/owners")
def get_god_mode_owners(db: Session = Depends(get_db), _=Depends(verify_admin)):
    gyms = db.query(models.Gym).all()
    
    # Group by owner identity (owner_email or email)
    owners_map = {}
    for g in gyms:
        o_email = g.owner_email or g.email
        if o_email not in owners_map:
            owners_map[o_email] = {
                "owner_name": g.owner_name,
                "owner_email": o_email,
                "phone": g.phone,
                "branches": []
            }
        
        m_count = db.query(func.count(models.Member.id)).filter(models.Member.gym_id == g.id).scalar() or 0
        rev = db.query(func.sum(models.Payment.amount)).filter(models.Payment.gym_id == g.id, models.Payment.payment_status == "completed").scalar() or Decimal("0.00")
        pending_rev = db.query(func.sum(models.Payment.amount)).filter(models.Payment.gym_id == g.id, models.Payment.payment_status == "pending").scalar() or Decimal("0.00")
        
        owners_map[o_email]["branches"].append({
            "id": g.id,
            "name": g.name,
            "business_type": g.business_type or "gym",
            "city": g.city or g.village_or_town or "Guwahati",
            "state": g.state or "Assam",
            "district": g.district or "Kamrup",
            "pincode": g.pincode or "781001",
            "phone": g.phone,
            "upi_id": g.upi_id or "Not set",
            "subscription_status": g.subscription_status or "trial",
            "subscription_end": str(g.subscription_end) if g.subscription_end else "Trial",
            "members_count": m_count,
            "revenue": float(rev),
            "pending": float(pending_rev),
            "is_main_branch": g.is_main_branch if hasattr(g, 'is_main_branch') else True,
            "autopilot_enabled": g.autopilot_enabled if hasattr(g, 'autopilot_enabled') else True,
            "created_at": str(g.created_at.date()) if g.created_at else "N/A"
        })
    
    owners_list = []
    for email, o in owners_map.items():
        total_branches = len(o["branches"])
        active_branches = sum(1 for b in o["branches"] if b["subscription_status"] == "active")
        total_members = sum(b["members_count"] for b in o["branches"])
        total_revenue = sum(b["revenue"] for b in o["branches"])
        total_paid = active_branches * PLATFORM_FEE_PER_MONTH
        total_due = (total_branches - active_branches) * PLATFORM_FEE_PER_MONTH
        
        overall_status = "Active" if active_branches == total_branches else ("Partial Active" if active_branches > 0 else "Trial / Due")
        
        owners_list.append({
            "owner_name": o["owner_name"],
            "owner_email": o["owner_email"],
            "phone": o["phone"],
            "total_branches": total_branches,
            "active_branches": active_branches,
            "total_members": total_members,
            "total_revenue": total_revenue,
            "subscription_status": overall_status,
            "total_paid_to_platform": total_paid,
            "total_pending_to_platform": total_due,
            "branches": o["branches"]
        })
        
    return owners_list


# --- 7. GOD MODE: Full Administrative Branch Inspector ---
@router.get("/branches/{branch_id}/full-view")
def get_branch_full_administrative_view(branch_id: int, db: Session = Depends(get_db), _=Depends(verify_admin)):
    gym = db.query(models.Gym).filter(models.Gym.id == branch_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Branch not found")
        
    members = db.query(models.Member).filter(models.Member.gym_id == branch_id).all()
    leads = db.query(models.Lead).filter(models.Lead.gym_id == branch_id).all()
    payments = db.query(models.Payment).filter(models.Payment.gym_id == branch_id).all()
    invoices = db.query(models.Invoice).filter(models.Invoice.gym_id == branch_id).all()
    staff = db.query(models.Staff).filter(models.Staff.gym_id == branch_id).all()
    audit_logs = db.query(models.AuditLog).filter(models.AuditLog.gym_id == branch_id).order_by(models.AuditLog.created_at.desc()).limit(20).all()
    docs = db.query(models.DocumentRecord).filter(models.DocumentRecord.gym_id == gym.id).order_by(models.DocumentRecord.created_at.desc()).limit(10).all()

    return {
        "branch": {
            "id": gym.id,
            "name": gym.name,
            "owner_name": gym.owner_name,
            "owner_email": gym.owner_email or gym.email,
            "phone": gym.phone,
            "business_type": gym.business_type,
            "address_line": gym.address_line,
            "state": gym.state,
            "district": gym.district,
            "city": gym.city,
            "pincode": gym.pincode,
            "upi_id": gym.upi_id,
            "subscription_status": gym.subscription_status,
            "subscription_end": str(gym.subscription_end) if gym.subscription_end else None,
            "autopilot_enabled": gym.autopilot_enabled if hasattr(gym, 'autopilot_enabled') else True
        },
        "stats": {
            "members_count": len(members),
            "leads_count": len(leads),
            "total_revenue": sum(float(p.amount) for p in payments if p.payment_status == "completed"),
            "staff_count": len(staff),
            "invoices_count": len(invoices)
        },
        "recent_members": [{"id": m.id, "name": m.full_name, "phone": m.phone, "plan": m.membership_type, "active": m.is_active} for m in members[:10]],
        "recent_payments": [{"id": p.id, "amount": float(p.amount), "mode": p.payment_mode, "status": p.payment_status, "date": str(p.payment_date)} for p in payments[:10]],
        "recent_audit": [{"action": a.action, "actor": a.actor_name, "details": a.details, "time": str(a.created_at)} for a in audit_logs],
        "recent_documents": [{"id": d.id, "type": d.doc_type, "title": d.title, "time": str(d.created_at)} for d in docs]
    }


# --- 8. GOD MODE: 1-Click Activate Branch ---
@router.post("/branches/{branch_id}/activate")
def activate_branch_admin(branch_id: int, days: int = 30, db: Session = Depends(get_db), _=Depends(verify_admin)):
    from datetime import date, timedelta
    gym = db.query(models.Gym).filter(models.Gym.id == branch_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Branch not found")
        
    gym.subscription_status = "active"
    gym.subscription_start = date.today()
    gym.subscription_end = date.today() + timedelta(days=days)
    db.commit()
    db.refresh(gym)
    return {"status": "success", "message": f"Branch '{gym.name}' activated for {days} days.", "branch_id": branch_id}
# --- 9. GOD MODE: Bulk Activate Owner's Branches ---
@router.post("/owners/{owner_email}/bulk-activate")
def bulk_activate_owner_branches(owner_email: str, days: int = 30, db: Session = Depends(get_db), _=Depends(verify_admin)):
    from datetime import date, timedelta
    
    gyms = db.query(models.Gym).filter(
        (models.Gym.owner_email == owner_email) | (models.Gym.email == owner_email)
    ).all()
    
    if not gyms:
        raise HTTPException(status_code=404, detail="No branches found for this owner")
    
    for gym in gyms:
        gym.subscription_status = "active"
        gym.subscription_start = date.today()
        gym.subscription_end = date.today() + timedelta(days=days)
        
    db.commit()
    
    return {
        "status": "success", 
        "message": f"Successfully activated {len(gyms)} branches for {days} days.", 
        "branches_updated": len(gyms)
    }
