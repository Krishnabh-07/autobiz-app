"""
whatsapp_cloud.py — Official Meta WhatsApp Cloud API Dispatcher & Simulator
Handles automated background dispatch to real WhatsApp numbers via Meta Graph API
or simulated dispatch queue when credentials are in test mode.
"""

import os
import httpx
import logging

logger = logging.getLogger("whatsapp_cloud")

# Meta WhatsApp Cloud API Configuration
WHATSAPP_TOKEN = os.getenv("WHATSAPP_CLOUD_API_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
META_GRAPH_URL = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# Global Dispatch Audit Log
DISPATCH_HISTORY = []


async def send_whatsapp_message(to_phone: str, message_text: str, sender_name: str = "AutoBiz AI", channel: str = "channel_2"):
    """
    Sends an automated WhatsApp message in the background.
    - If Meta WhatsApp credentials are present, sends via official API.
    - Also records into DISPATCH_HISTORY audit trail for live dashboard view.
    """
    clean_phone = to_phone.replace("+", "").replace("-", "").replace(" ", "")
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone

    dispatch_record = {
        "to_phone": clean_phone,
        "sender": sender_name,
        "channel": channel,  # channel_1 (Krishnabh to Owner) or channel_2 (Owner to Member)
        "message": message_text,
        "status": "dispatched",
        "timestamp": None
    }

    from datetime import datetime
    dispatch_record["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # If real WhatsApp Cloud API token is configured, make the HTTP request
    if WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_phone,
                    "type": "text",
                    "text": {"body": message_text}
                }
                res = await client.post(META_GRAPH_URL, headers=headers, json=payload, timeout=10.0)
                if res.status_code == 200:
                    dispatch_record["status"] = "delivered_via_meta_api"
                else:
                    dispatch_record["status"] = f"meta_api_response_{res.status_code}"
        except Exception as e:
            logger.error(f"WhatsApp API dispatch error: {e}")
            dispatch_record["status"] = "simulated_dispatch"
    else:
        # Automated Background Dispatch Log
        dispatch_record["status"] = "automated_background_dispatched"

    DISPATCH_HISTORY.insert(0, dispatch_record)
    if len(DISPATCH_HISTORY) > 100:
        DISPATCH_HISTORY.pop()

    return dispatch_record


def get_dispatch_history(channel: str = None, limit: int = 20):
    if channel:
        return [d for d in DISPATCH_HISTORY if d.get("channel") == channel][:limit]
    return DISPATCH_HISTORY[:limit]
