import sqlite3

db_path = r'backend\autobiz.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

delete_order = ['bulk_subscription_payments','customer_timeline_events','document_records','audit_logs','reviews','booking_slots','invoices','attendance','payments','leads','staff','service_plans','members','password_reset_tokens','otp_verifications','gyms']

for t in delete_order:
    if t in tables:
        cur.execute(f'DELETE FROM {t}')
        print(f'Cleared {t}: {cur.rowcount} rows')

conn.commit()
conn.close()
print('ALL DONE - data is 0!')
