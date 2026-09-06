import os, sys
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from database import SessionLocal
import models

def reset_all():
    db = SessionLocal()
    print('\n Resetting AutoBiz Database...\n')

    tables = [
        models.BulkSubscriptionPayment,
        models.CustomerTimelineEvent,
        models.DocumentRecord,
        models.AuditLog,
        models.Review,
        models.BookingSlot,
        models.Invoice,
        models.Attendance,
        models.Payment,
        models.Lead,
        models.Staff,
        models.ServicePlan,
        models.Member,
        models.PasswordResetToken,
        models.OTPVerification,
        models.Gym,
    ]

    for model in tables:
        count = db.query(model).count()
        db.query(model).delete()
        print(f'  Cleared {model.__tablename__}: {count} rows deleted')

    db.commit()
    db.close()
    print('\n Database reset complete! All data = 0\n')

if __name__ == '__main__':
    reset_all()
