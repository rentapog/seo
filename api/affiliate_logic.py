# --- Referral Assignment Logic (to use in your registration/signup flow) ---
from .models import User, db

ADMIN_USERNAME = 'seobrain'

def get_admin_user():
    return User.query.filter_by(username=ADMIN_USERNAME).first()

def assign_referral(new_user, affiliate):
    # Count active referrals for this affiliate
    active_referrals = affiliate.referrals.filter_by(is_active=True).count()
    admin = get_admin_user()
    if active_referrals == 1 and admin:  # 2nd referral (0-based index)
        new_user.referrer_id = admin.id
    else:
        new_user.referrer_id = affiliate.id
    db.session.add(new_user)
    db.session.commit()

# --- Daily Payment Scheduler Logic (to run once per day, e.g. with APScheduler or cron) ---
from .paypal import create_paypal_order

def trigger_daily_payments():
    affiliates = User.query.filter(User.is_active == True).all()
    for affiliate in affiliates:
        # Count all active referrals (including passed-up)
        total_referrals = affiliate.referrals.filter_by(is_active=True).count()
        if total_referrals >= 3:
            # Example: $10 daily payment, customize as needed
            amount = 10
            description = f"Daily payment for affiliate {affiliate.username}"
            # Only trigger if affiliate has a PayPal ID
            if affiliate.paypal_id:
                create_paypal_order(amount, description)
