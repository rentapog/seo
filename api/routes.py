from flask import Blueprint, session, redirect, url_for, render_template, request, jsonify, current_app
import secrets
import hashlib
import requests
import os
import base64
import hmac
from datetime import datetime
from .app import db
from .models import User, Referral, Package, UserPackage, Payment
from .paypal import create_paypal_order

bp = Blueprint('main', __name__)

# Route for /payment to render the payment page
@bp.route('/payment')
def payment():
    return render_template('payment.html')

# Route for /privacy-policy
@bp.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

# Route for /terms
@bp.route('/terms')
def terms():
    return render_template('terms.html')
# Route for /packages to render the main packages page
@bp.route('/packages')
def packages():
    return render_template('packages.html')
# --- Blueprint must be defined before any @bp.route decorators ---
# Sales page route
@bp.route('/sales')
def sales():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    user = User.query.get(session['user_id'])
    packages = Package.query.all()
    # Prepare features for each package (assuming a 'features' attribute or list)
    package_list = []
    for pkg in packages:
        # If features is a string, split by newline or comma; else use as is
        features = getattr(pkg, 'features', [])
        if isinstance(features, str):
            features = [f.strip() for f in features.split('\n') if f.strip()]
        package_list.append({
            'id': pkg.id,
            'name': pkg.name,
            'price': pkg.price,
            'features': features
        })
    return render_template('sales.html', user=user, packages=package_list)
# --- Blueprint must be defined before any @bp.route decorators ---
# Login route
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password_hash == hashlib.sha256(password.encode()).hexdigest():
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.dashboard'))
        return render_template('login.html', message='Invalid username or password.')
    return render_template('login.html')

# Logout route
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

# Dashboard route (protected)
@bp.route('/dashboard')
def dashboard():
    # Assume user is loaded from session
    user = User.query.filter_by(id=session.get('user_id')).first()
    if not user:
        return redirect(url_for('main.login'))
    # Count active referrals
    referral_count = user.referrals.filter_by(is_active=True).count()
    # Example: get user's package and daily payout
    package = Package.query.filter_by(id=user.package_id).first() if user.package_id else None
    daily_earning = (package.daily_payment_amount if package else 0) * referral_count
    weekly_earning = daily_earning * 7
    monthly_earning = daily_earning * 30
    yearly_earning = daily_earning * 365
    total_earned = 0  # You can sum Payment records for this user if you track payouts
    return render_template('dashboard.html', user=user, referral_count=referral_count, daily_earning=daily_earning, weekly_earning=weekly_earning, monthly_earning=monthly_earning, yearly_earning=yearly_earning, total_earned=total_earned)
# Password reset route
@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    from flask import render_template, request
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            return render_template('reset_password.html', message='No account found with that email.')
        # Generate a reset token (simple, for demo; use JWT or similar for production)
        import secrets
        token = secrets.token_urlsafe(32)
        # Store token in user session or DB if you want to validate later (not shown here)
        reset_link = f"https://admin.seobrainai.com/reset-password/{token}"
        subject = "Password Reset Request"
        body = f"Hello,\n\nTo reset your password, click the link below:\n{reset_link}\n\nIf you did not request this, ignore this email."
        send_resend_email(email, subject, body)
        return render_template('reset_password.html', message='A reset link has been sent to your email.')
    return render_template('reset_password.html')
import secrets
import hashlib
import requests
import os
# Utility function to send email via Resend API
def send_resend_email(to_email, subject, body_text, from_email="noreply@admin.seobrainai.com"):
    api_key = os.getenv("RESEND_API_KEY")
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # Always use verified sender address
    data = {
        "from": "noreply@admin.seobrainai.com",
        "to": [to_email],
        "subject": subject,
        "text": body_text
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Resend email failed: {e}")
        return False

# Root route for health check or homepage
@bp.route('/')
def index():
    from flask import render_template
    return render_template('packages.html')

# PayPal Webhook endpoint
@bp.route('/webhook/paypal', methods=['POST'])
def paypal_webhook():
    # Webhook signature verification
    webhook_id = os.getenv('PAYPAL_WEBHOOK_ID')
    transmission_id = request.headers.get('Paypal-Transmission-Id')
    transmission_time = request.headers.get('Paypal-Transmission-Time')
    cert_url = request.headers.get('Paypal-Cert-Url')
    auth_algo = request.headers.get('Paypal-Auth-Algo')
    transmission_sig = request.headers.get('Paypal-Transmission-Sig')
    webhook_event = request.get_data(as_text=True)
    actual_body = request.get_data()

    # For local verification, use the webhook secret (deprecated, but simple for dev)
    webhook_secret = os.getenv('PAYPAL_WEBHOOK_SECRET')
    if webhook_secret:
        expected_sig = base64.b64encode(hmac.new(webhook_secret.encode(), actual_body, hashlib.sha256).digest()).decode()
        if not hmac.compare_digest(expected_sig, transmission_sig or ''):
            return jsonify({'error': 'Invalid webhook signature'}), 400

    # Continue with event handling
    event = request.json
    event_type = event.get('event_type')
    resource = event.get('resource', {})
    # Example: handle payment capture completed
    if event_type == 'CHECKOUT.ORDER.APPROVED' or event_type == 'PAYMENT.CAPTURE.COMPLETED':
        order_id = resource.get('id')
        # Find payment by PayPal order/txn id
        payment = Payment.query.filter_by(paypal_txn_id=order_id).first()
        if payment:
            payment.payment_date = datetime.utcnow()
            db.session.commit()
            return jsonify({'message': 'Payment recorded'}), 200
        return jsonify({'error': 'Payment not found'}), 404
    # Add more event types as needed
    return jsonify({'message': 'Event received'}), 200

@bp.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    username = data.get('username')
    first_name = data.get('first_name')
    ref_code = data.get('ref_code')  # referrer's email, id, or username
    package_id = data.get('package_id')
    # Ensure 'seobrain' admin user exists
    admin_user = User.query.filter_by(username='seobrain').first()
    if not admin_user:
        admin_user = User(
            email='admin@seobrainai.com',
            username='seobrain',
            password_hash=hashlib.sha256(secrets.token_urlsafe(10).encode()).hexdigest(),
            is_active=True
        )
        db.session.add(admin_user)
        db.session.commit()
    if not email or not package_id or not username or not first_name:
        return jsonify({'error': 'Missing required fields'}), 400
    if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
        return jsonify({'error': 'User already exists'}), 400
    # Generate random password and hash it
    password = secrets.token_urlsafe(10)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    user = User(email=email, username=username, password_hash=password_hash)
    # Always pay admin fee to admin
    if admin_user:
        admin_payment = Payment(
            payer_id=user.id,
            payee_id=admin_user.id,
            package_id=package_id,
            amount=Package.query.get(package_id).price,
            payment_type='activation',
            payment_date=datetime.utcnow()
        )
        db.session.add(admin_payment)
        db.session.commit()
    # Referral logic
    if ref_code:
        referrer = User.query.filter((User.email==ref_code)|(User.id==ref_code)|(User.username==ref_code)).first()
        if referrer:
            user.referrer_id = referrer.id
    db.session.add(user)
    db.session.commit()
    # Assign package
    up = UserPackage(user_id=user.id, package_id=package_id)
    db.session.add(up)
    db.session.commit()
    # Track referral: always assign referral to the user who brought them in
    if user.referrer_id:
        referral = Referral(referrer_id=user.referrer_id, referred_id=user.id)
        db.session.add(referral)
        db.session.commit()
    # Generate affiliate link
    affiliate_link = f"https://seobrainai.com/?ref={username}"
    # Send welcome email via Resend
    subject = "Welcome to SEOBRAIN! Your Dashboard & Next Steps"
    dashboard_link = f"https://admin.seobrainai.com/dashboard/{username}"
    packages_summary = """
Starter: 10 GB SSD Storage – $20
Basic: 25 GB SSD Storage – $49
Pro: 50 GB SSD Storage – $99
Elite: 100 GB SSD Storage – $299
Empire: 250 GB SSD Storage – $499
Starter 1000: 500 GB SSD Storage – $1,000
Ultra 2000: 1 TB SSD Storage – $2,000
"""
    body = f"""
Hello {first_name},

Welcome to SEOBRAIN! Your account is ready.

Your login password: {password}
Your dashboard: {dashboard_link}
Your affiliate link: {affiliate_link}

What to do next:
1. Log in to your dashboard using your username and password above.
2. Explore your dashboard to see your affiliate link and available packages.
3. To get paid, set up your PayPal account in your dashboard (go to 'Settings' > 'Payout Method' and enter your PayPal email).
4. Share your affiliate link to invite others and earn rewards automatically.
5. Upgrade your package anytime from your dashboard for more features and higher earnings.

Available Packages:
{packages_summary}

If you need help, reply to this email or visit our support page.

Best regards,
The SEOBRAIN Team
    """
    send_resend_email(email, subject, body)
    return jsonify({'message': 'User registered', 'user_id': user.id, 'affiliate_link': affiliate_link})

@bp.route('/referrals/<int:user_id>')
def get_referrals(user_id):
    count = Referral.query.filter_by(referrer_id=user_id).count()
    return jsonify({'referral_count': count})


# Initiate a PayPal payment (activation or daily)
@bp.route('/pay', methods=['POST'])
def pay():
    data = request.json
    user_id = data.get('user_id')
    package_id = data.get('package_id')
    payment_type = data.get('payment_type', 'activation')
    user = User.query.get(user_id)
    package = Package.query.get(package_id)
    if not user or not package:
        return jsonify({'error': 'Invalid user or package'}), 400
    amount = package.price if payment_type == 'activation' else package.daily_payment_amount
    desc = f"{package.name} Web Hosting Package ({payment_type.title()} Fee)"
    order = create_paypal_order(amount, desc)
    # Record payment intent (not captured yet)
    payment = Payment(
        payer_id=user.referrer_id if payment_type == 'daily' else user.id,
        payee_id=user.id,
        package_id=package.id,
        amount=amount,
        payment_type=payment_type,
        paypal_txn_id=order['id']
    )
    db.session.add(payment)
    db.session.commit()
    return jsonify({'paypal_order': order})

# Activate daily payments after 3 paid referrals
@bp.route('/activate-daily/<int:user_id>', methods=['POST'])
def activate_daily(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    # Count paid referrals (referrals with activation payment to admin)
    referrals = Referral.query.filter_by(referrer_id=user.id).all()
    paid_count = 0
    for r in referrals:
        # Query for admin_user inside this function to avoid undefined variable
        admin_user = User.query.filter_by(username='seobrain').first()
        if not admin_user:
            continue
        payment = Payment.query.filter_by(payer_id=r.referred_id, payee_id=admin_user.id, payment_type='activation').first()
        if payment:
            paid_count += 1
    if paid_count >= 3:
        up = UserPackage.query.filter_by(user_id=user.id).first()
        if up and not up.daily_payment_active:
            up.daily_payment_active = True
            up.daily_payment_start_date = datetime.utcnow()
            db.session.commit()
            return jsonify({'message': 'Daily payments activated'})
        return jsonify({'message': 'Already active'})
    return jsonify({'message': 'Not enough paid referrals', 'paid_count': paid_count})

@bp.route('/affiliate-earnings')
def affiliate_earnings():
    # Example membership levels and daily payout rates
    levels = [
        {'name': 'Starter', 'daily': 2},
        {'name': 'Pro', 'daily': 5},
        {'name': 'Elite', 'daily': 10}
    ]
    ref_counts = [3, 5, 10, 15, 20, 50]
    return render_template('affiliate_earnings.html', levels=levels, ref_counts=ref_counts)
