"""
bot_ai.py — WhatsApp AI Engine & Trending Instagram Meme Message Generator
Generates engaging, viral, polite, and humorous meme-style WhatsApp messages for:
1. Trial follow-ups (Ask for plan selection)
2. Customer membership 3-day expiry alerts
3. Owner platform subscription 3-day expiry alerts
4. Owner subscription defaulter alerts
"""

import random
import os
import logging

logger = logging.getLogger("bot_ai")

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

# Multi-Industry Emojis & Vocabulary
INDUSTRY_VOCAB = {
    "gym": {
        "item": "membership",
        "action": "workout",
        "loss": "gains aur momentum ud jayega",
        "icon": "🏋️💪",
        "motive": "Bro is locked in! 🚀"
    },
    "clinic": {
        "item": "treatment / routine checkup",
        "action": "consultation",
        "loss": "health routine miss ho jayegi",
        "icon": "🏥🩺",
        "motive": "Good health is the ultimate flex! ✨"
    },
    "salon": {
        "item": "grooming & self-care session",
        "action": "hair & spa care",
        "loss": "glow routine break ho jayegi",
        "icon": "💇✨",
        "motive": "Glow-up game on point! 💅"
    },
    "coaching": {
        "item": "course batch & syllabus",
        "action": "classes & tests",
        "loss": "rank aur study streak toot jayegi",
        "icon": "🏫📚",
        "motive": "Topper mindset only! 🎯"
    },
    "dental": {
        "item": "dental hygiene care",
        "action": "cleaning & checkup",
        "loss": "million-dollar smile miss ho jayegi",
        "icon": "🦷😁",
        "motive": "Keep shining that smile! 🌟"
    }
}

def generate_with_gemini(prompt: str, fallback_func, *args, **kwargs) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and genai:
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                )
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini generation error: {e}. Falling back to templates.")
            pass
    return fallback_func(*args, **kwargs)


def get_trial_followup_message_template(customer_name: str, business_name: str, business_type: str = "gym", plans: dict = None) -> str:
    if not plans:
        plans = {"1_month": "₹800", "3_months": "₹2,000", "7_months": "₹4,000"}

    vocab = INDUSTRY_VOCAB.get(business_type.lower(), INDUSTRY_VOCAB["gym"])
    
    templates = [
        (
            f"Namaste {customer_name} ji! {vocab['icon']}\n"
            f"Hope aapka {business_name} mein trial session zabardast raha! 🔥\n\n"
            f"\"Motivation is temporary, Discipline is forever!\" — aur aapka transformation rukna nahi chahiye! 💪\n\n"
            f"Apne hisaab se best plan choose kijiye:\n"
            f"🥉 1 Month  — {plans.get('1_month', '₹800')}\n"
            f"🥈 3 Months — {plans.get('3_months', '₹2,000')} (Most Popular 🔥)\n"
            f"🥇 7 Months — {plans.get('7_months', '₹4,000')} (VIP Best Value 👑)\n\n"
            f"👉 Bas 1, 2 ya 3 reply kijiye aur kal se seedha start ho jaiye! Warm regards, Team {business_name} ✨"
        ),
        (
            f"Hey {customer_name}! 🚀 Welcome to {business_name}! {vocab['icon']}\n\n"
            f"Aaj ka trial dekh kar laga: Bro is truly locked in! 💯\n\n"
            f"Kal se official streak shuru karte hain. Choose your plan:\n"
            f"1️⃣ 1 Month  : {plans.get('1_month', '₹800')}\n"
            f"2️⃣ 3 Months : {plans.get('3_months', '₹2,000')}\n"
            f"3️⃣ 7 Months : {plans.get('7_months', '₹4,000')}\n\n"
            f"Reply with plan number and let's make it happen! 🌟"
        ),
        (
            f"Arrey {customer_name} bhai! {vocab['icon']} {business_name} par visit karne ke liye shukriya!\n\n"
            f"\"Tu karein ya na karein, waqt toh guzar hi jayega!\" Toh kyun na best version banne pe lagayein? 😂🔥\n\n"
            f"Lock your spot:\n"
            f"• 1 Month: {plans.get('1_month', '₹800')}\n"
            f"• 3 Months: {plans.get('3_months', '₹2,000')}\n"
            f"• 7 Months: {plans.get('7_months', '₹4,000')}\n\n"
            f"Reply kijiye aur journey continue kijiye! 🚀"
        )
    ]
    return random.choice(templates)


def get_trial_followup_message(customer_name: str, business_name: str, business_type: str = "gym", plans: dict = None) -> str:
    """Generates polite, engaging, trending meme-style post-trial conversion message."""
    prompt = f"Write a short, engaging, viral meme-style WhatsApp message in Hinglish to {customer_name} from {business_name} ({business_type}). They just completed a trial. Ask them to choose a plan to continue their streak. The plans are: {plans if plans else '1 Month (800), 3 Months (2000), 7 Months (4000)'}. Use emojis."
    return generate_with_gemini(prompt, get_trial_followup_message_template, customer_name, business_name, business_type, plans)


def get_customer_expiry_reminder_template(customer_name: str, business_name: str, business_type: str = "gym", days_left: int = 3, payment_link: str = "wa.me/pay") -> str:
    vocab = INDUSTRY_VOCAB.get(business_type.lower(), INDUSTRY_VOCAB["gym"])

    templates = [
        (
            f"Namaste {customer_name} ji! ⏳ Friendly reminder from {business_name} {vocab['icon']}\n\n"
            f"Aapka plan bas {days_left} din mein complete hone wala hai!\n\n"
            f"\"Consistency hi asli flex hai!\" — apna hard-earned momentum aur streak mat tootne dijiye! 🔥\n\n"
            f"Seamless renewal ke liye yahan tap karein: {payment_link} 🚀\n"
            f"Always supporting your journey! — Team {business_name}"
        ),
        (
            f"Oye {customer_name} bhai! 💀 {business_name} ka tera plan bas {days_left} din mein khatam hone wala hai!\n\n"
            f"\"Gains bante bante break lag gaya\" wala dukh mat jhelna! 😂\n\n"
            f"Quick 10-second renewal karein aur streak maintain karein: {payment_link} {vocab['icon']}\n"
            f"Let's keep grinding! 💪"
        ),
        (
            f"Hey {customer_name}! 🚨 Polite Alert: Sirf {days_left} din bache hain aapke {business_name} {vocab['item']} mein!\n\n"
            f"Self-improvement is an investment, not an expense! 🌟\n\n"
            f"Renew in 1-Click here: {payment_link} {vocab['icon']}\n"
            f"See you on the floor! ✨"
        )
    ]
    return random.choice(templates)


def get_customer_expiry_reminder(customer_name: str, business_name: str, business_type: str = "gym", days_left: int = 3, payment_link: str = "wa.me/pay") -> str:
    """Generates polite, encouraging, viral meme-style customer renewal reminder (3 days before)."""
    prompt = f"Write a short, engaging, viral meme-style WhatsApp message in Hinglish to {customer_name} from {business_name} ({business_type}). Remind them that their plan expires in {days_left} days. Encourage them to renew via this link: {payment_link}. Be polite but use Gen Z slang and emojis."
    return generate_with_gemini(prompt, get_customer_expiry_reminder_template, customer_name, business_name, business_type, days_left, payment_link)


def get_owner_subscription_reminder_template(owner_name: str, business_name: str, days_left: int = 3, payment_link: str = "wa.me/pay_krishnabh") -> str:
    templates = [
        (
            f"Namaste {owner_name} ji! 👑 Krishnabh here from AutoBiz AI.\n\n"
            f"Aapke {business_name} ka autopilot SaaS subscription bas {days_left} din mein renew hone wala hai! 🚀\n\n"
            f"Tension-free automated leads, Zero Jhooth member tracking aur 24/7 WhatsApp AI bot active rakhne ke liye abhi renew karein (₹1,500/month): {payment_link} ✨\n\n"
            f"Wishing massive business growth! 💰"
        ),
        (
            f"Bhai {owner_name}! 🚀 {business_name} ka automation mode 10/10 chal raha hai!\n\n"
            f"Bas {days_left} din bache hain monthly renewal mein. Zero hassle & 100% Peace of mind active rakhein: {payment_link} (₹1,500 only) 🔥\n\n"
            f"Keep winning! 👑"
        )
    ]
    return random.choice(templates)


def get_owner_subscription_reminder(owner_name: str, business_name: str, days_left: int = 3, payment_link: str = "wa.me/pay_krishnabh") -> str:
    """Generates polite + trending viral subscription renewal alert for Business Owners from Krishnabh."""
    prompt = f"Write a short WhatsApp message in Hinglish to {owner_name}, owner of {business_name}, from Krishnabh at AutoBiz AI. Remind them their SaaS subscription expires in {days_left} days. Ask them to renew for ₹1,500/month using link: {payment_link}. Use emojis and be encouraging about business growth."
    return generate_with_gemini(prompt, get_owner_subscription_reminder_template, owner_name, business_name, days_left, payment_link)


def get_defaulter_nudge_message_template(owner_name: str, business_name: str, payment_link: str = "wa.me/pay_krishnabh") -> str:
    templates = [
        (
            f"Hey {owner_name} bhai! 💀 {business_name} ka AutoBiz subscription expire ho gaya hai!\n\n"
            f"Autopilot features pause hone se pehle 1-click mein renew karwa lo: {payment_link} (₹1,500/month) 🚀\n\n"
            f"Let's keep the business automated! 👑"
        ),
        (
            f"Namaste {owner_name} ji! Aapka {business_name} dashboard subscription end ho chuka hai. ✨\n\n"
            f"Uninterrupted automated WhatsApp bot aur CRM reports ke liye please renew: {payment_link} (₹1,500 only) 💼"
        )
    ]
    return random.choice(templates)


def get_defaulter_nudge_message(owner_name: str, business_name: str, payment_link: str = "wa.me/pay_krishnabh") -> str:
    """Generates polite, humorous defaulter message for expired business accounts."""
    prompt = f"Write a short, polite WhatsApp message in Hinglish to {owner_name}, owner of {business_name}, notifying them that their AutoBiz subscription has expired. Ask them to renew at {payment_link} to keep their business automated. Keep it light."
    return generate_with_gemini(prompt, get_defaulter_nudge_message_template, owner_name, business_name, payment_link)
