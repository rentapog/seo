# Quick script to print all usernames and emails in the User table
from app import app, db
from models import User

with app.app_context():
    users = User.query.all()
    for user in users:
        print(f"Username: {user.username}, Email: {user.email}")
