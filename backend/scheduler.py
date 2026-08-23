"""
scheduler.py — Automated Background AI Scheduler for Channel 1 & Channel 2
Runs 24/7 in background to trigger automated WhatsApp messages:
Channel 1: Krishnabh -> Owner (Subscription Expiry & Defaulter alerts)
Channel 2: Gym Owner -> Member / Lead (3-day expiry & Post-trial follow-up)
"""

import asyncio
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
import database
import models
import bot_ai
import whatsapp_cloud
import logging

logger = logging.getLogger("scheduler")
scheduler = BackgroundScheduler()


def run_channel_1_superadmin_jobs():
    """
    CHANNEL 1 (Krishnabh to Owner):
    Scans business owners with subscription expiring in 3 days or expired.
    Dispatches automated WhatsApp meme reminder on Krishnabh's behalf.
    """
    db: Session = database.SessionLocal()
    try:
        today = date.today()
        three_days = today + timedelta(days=3)

        # 1. Expiring in 3 days
        expiring_gyms = db.query(models.Gym).filter(
            models.Gym.subscription_end.between(today, three_days)
        ).all()

        for gym in expiring_gyms:
            days_left = (gym.subscription_end - today).days if gym.subscription_end else 0
            msg = bot_ai.get_owner_subscription_reminder(
                owner_name=gym.owner_name,
                business_name=gym.name,
                days_left=max(days_left, 1)
            )
            # Run async send inside sync job
            asyncio.run(whatsapp_cloud.send_whatsapp_message(
                to_phone=gym.phone,
                message_text=msg,
                sender_name="Krishnabh (Platform Owner)",
                channel="channel_1"
            ))

        # 2. Defaulters / Expired
        expired_gyms = db.query(models.Gym).filter(
            models.Gym.subscription_status == "expired"
        ).all()

        for gym in expired_gyms:
            msg = bot_ai.get_defaulter_nudge_message(
                owner_name=gym.owner_name,
                business_name=gym.name
            )
            asyncio.run(whatsapp_cloud.send_whatsapp_message(
                to_phone=gym.phone,
                message_text=msg,
                sender_name="Krishnabh (Platform Owner)",
                channel="channel_1"
            ))

    except Exception as e:
        logger.error(f"Channel 1 automation error: {e}")
    finally:
        db.close()


def run_channel_2_owner_to_member_jobs():
    """
    CHANNEL 2 (Gym Owner to Member):
    1. Scans members whose plan expires in 3 days -> Sends meme alert on Gym's behalf.
    2. Scans leads who took trial today -> Sends meme follow-up with plans on Gym's behalf.
    """
    db: Session = database.SessionLocal()
    try:
        today = date.today()
        three_days = today + timedelta(days=3)

        # 1. Members Expiring in 3 Days
        expiring_members = db.query(models.Member).filter(
            models.Member.end_date.between(today, three_days),
            models.Member.is_active == True
        ).all()

        for m in expiring_members:
            gym = m.gym
            days_left = (m.end_date - today).days if m.end_date else 0
            msg = bot_ai.get_customer_expiry_reminder(
                customer_name=m.full_name,
                business_name=gym.name if gym else "Our Club",
                business_type=gym.business_type if gym else "gym",
                days_left=max(days_left, 1)
            )
            asyncio.run(whatsapp_cloud.send_whatsapp_message(
                to_phone=m.phone,
                message_text=msg,
                sender_name=gym.name if gym else "Gym Owner",
                channel="channel_2"
            ))

        # 2. Post-Trial Follow-up for Leads (trial_done)
        trial_leads = db.query(models.Lead).filter(
            models.Lead.status.in_(["trial_done", "new"])
        ).all()

        for l in trial_leads:
            gym = l.gym
            msg = bot_ai.get_trial_followup_message(
                customer_name=l.name,
                business_name=gym.name if gym else "Our Club",
                business_type=gym.business_type if gym else "gym"
            )
            asyncio.run(whatsapp_cloud.send_whatsapp_message(
                to_phone=l.phone,
                message_text=msg,
                sender_name=gym.name if gym else "Gym Owner",
                channel="channel_2"
            ))

    except Exception as e:
        logger.error(f"Channel 2 automation error: {e}")
    finally:
        db.close()


def trigger_all_automations_now():
    """Manual or API-triggered immediate execution of both channels."""
    run_channel_1_superadmin_jobs()
    run_channel_2_owner_to_member_jobs()
    return {"status": "success", "message": "Channel 1 & Channel 2 automated dispatches executed successfully!"}


def start_scheduler():
    """Starts the background scheduler running daily at 09:00 AM and every hour."""
    if not scheduler.running:
        scheduler.add_job(run_channel_1_superadmin_jobs, 'cron', hour=9, minute=0, id='channel_1_daily')
        scheduler.add_job(run_channel_2_owner_to_member_jobs, 'cron', hour=9, minute=5, id='channel_2_daily')
        scheduler.start()
        logger.info("AutoBiz Background Scheduler Started Successfully!")
