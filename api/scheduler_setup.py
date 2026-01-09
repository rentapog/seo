# APScheduler setup for daily affiliate payments
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from api.affiliate_logic import trigger_daily_payments

# This should be in your main app file (e.g., app.py or wsgi.py)
def start_scheduler(app: Flask):
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=lambda: trigger_daily_payments(), trigger='interval', days=1)
    scheduler.start()
    # Shut down the scheduler when exiting the app
    import atexit
    atexit.register(lambda: scheduler.shutdown())

# In your app factory or main run block, call start_scheduler(app)
# Example:
# app = create_app()
# start_scheduler(app)
# app.run()
