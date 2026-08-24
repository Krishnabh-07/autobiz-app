import sys
import os
sys.path.insert(0, os.path.abspath("."))
import random
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print("--- TESTING ALL ADVANCED ENTERPRISE SAAS FEATURES ---")

# 1. Test Static Routes & Storefronts
print("1. Testing Static HTML Pages & Storefront Routes...")
routes = [
    "/", "/dashboard.html", "/explore.html", "/customer_portal.html",
    "/business_storefront.html", "/b/1", "/business/1",
    "/privacy.html", "/terms.html", "/support.html"
]
for r in routes:
    res = client.get(r)
    assert res.status_code == 200, f"Route {r} failed with {res.status_code}"
print("   [PASS] All Static & Storefront Routes OK!")

# 2. Test Auth & Registration
print("2. Testing Registration and Login...")
test_phone = f"999{random.randint(1000000, 9999999)}"
test_email = f"tester_{random.randint(1000, 9999)}@autobiz.ai"

reg_res = client.post("/auth/register", json={
    "name": "Elite Health & Dental Clinic",
    "owner_name": "Dr. Sharma",
    "phone": test_phone,
    "email": test_email,
    "password": "password123",
    "business_type": "clinic",
    "city": "Guwahati"
})
assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
biz_data = reg_res.json()
biz_id = biz_data["id"]

# Login to get JWT
login_res = client.post("/auth/login", data={
    "username": test_email,
    "password": "password123"
})
assert login_res.status_code == 200, f"Login failed: {login_res.text}"
auth_data = login_res.json()
token = auth_data["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"   [PASS] Auth Register & Login OK! (Tenant ID: {biz_id})")

# 3. Test Onboarding Wizard API
print("3. Testing Onboarding Wizard API (/gyms/me/onboarding)...")
onboard_res = client.post("/gyms/me/onboarding", headers=headers, json={
    "business_type": "clinic",
    "upi_id": "sharma@okhdfc",
    "timings": "08:00 AM - 09:00 PM",
    "primary_service": "Doctor Consultation & Checkup",
    "primary_price": 800.00
})
assert onboard_res.status_code == 200, f"Onboarding failed: {onboard_res.text}"
print("   [PASS] Onboarding API OK!")

# 4. Test Add Member & Audit Trail Logging
print("4. Testing Add Member + Audit Log Generation...")
mem_res = client.post("/members/add", headers=headers, json={
    "gym_id": biz_id,
    "full_name": "Rahul Verma",
    "phone": "9876500001",
    "email": "rahul@gmail.com",
    "membership_type": "Doctor Consultation",
    "start_date": "2026-08-24",
    "end_date": "2026-09-24"
})
assert mem_res.status_code == 200, f"Add Member failed: {mem_res.text}"
mem_id = mem_res.json()["id"]

# Check audit logs
audit_res = client.get("/audit-logs", headers=headers)
assert audit_res.status_code == 200, f"Audit logs failed: {audit_res.text}"
logs = audit_res.json()
assert len(logs) > 0, "No audit logs found"
print(f"   [PASS] Audit Logs OK! (Total events logged: {len(logs)})")

# 5. Test Booking Slots API
print("5. Testing Booking Slots API (/bookings/today & /bookings/slots)...")
slots_res = client.get("/bookings/today", headers=headers)
assert slots_res.status_code == 200, f"Booking slots failed: {slots_res.text}"
slots = slots_res.json()
assert len(slots) > 0, "No slots returned"
print(f"   [PASS] Booking Slots OK! ({len(slots)} batches active)")

# 6. Test Reviews & Reputation Hub API
print("6. Testing Reviews API (/reviews/feedback & /reviews)...")
rev_post = client.post("/reviews/feedback", json={
    "gym_id": biz_id,
    "customer_name": "Rahul Verma",
    "customer_phone": "9876500001",
    "rating": 5,
    "feedback_text": "Great treatment and very fast digital slot booking!"
})
assert rev_post.status_code == 200, f"Review post failed: {rev_post.text}"

rev_get = client.get("/reviews", headers=headers)
assert rev_get.status_code == 200, f"Review get failed: {rev_get.text}"
revs = rev_get.json()
assert len(revs) > 0, "No reviews found"
print(f"   [PASS] Reviews API OK! ({len(revs)} reviews recorded)")

# 7. Test Smart Notification Center API
print("7. Testing Smart Notification Center (/notifications/unread)...")
notif_res = client.get("/notifications/unread", headers=headers)
assert notif_res.status_code == 200, f"Notifications failed: {notif_res.text}"
notifs = notif_res.json()
print(f"   [PASS] Notifications API OK! ({notifs['count']} live alerts generated)")

# 8. Test AI Business OS Engine
print("8. Testing AI Business OS Endpoints...")
ai_q = client.post("/ai/query", headers=headers, json={"query": "How many active patients do we have?"})
assert ai_q.status_code == 200, f"AI query failed: {ai_q.text}"

ai_ins = client.get("/ai/insights", headers=headers)
assert ai_ins.status_code == 200, f"AI insights failed: {ai_ins.text}"

ai_off = client.post("/ai/generate-offer", headers=headers, json={"theme": "Health Checkup Special", "discount_pct": 25})
assert ai_off.status_code == 200, f"AI offer failed: {ai_off.text}"
print("   [PASS] AI Business OS OK!")

print("\n=============================================")
print("=============================================")
sys.exit(0)