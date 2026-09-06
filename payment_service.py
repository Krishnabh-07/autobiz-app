import os
import razorpay
import logging

logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay client: {e}")

def create_order(amount: float, currency: str = "INR", receipt: str = None) -> dict:
    """
    Create a Razorpay order. Amount should be in rupees, we convert to paise.
    """
    if not client:
        logger.warning(f"Razorpay not configured. Mocking order creation for {amount} {currency}")
        return {"id": "mock_order_id", "amount": int(amount * 100), "currency": currency}
        
    try:
        data = {
            "amount": int(amount * 100), # Razorpay accepts amount in paise
            "currency": currency,
            "receipt": receipt
        }
        order = client.order.create(data=data)
        return order
    except Exception as e:
        logger.error(f"Failed to create Razorpay order: {e}")
        return {}

def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """
    Verify payment signature from frontend callback.
    """
    if not client:
        return True # Mock success
        
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
    except Exception as e:
        logger.error(f"Payment verification failed: {e}")
        return False
