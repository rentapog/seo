import os
import requests
from flask import current_app
from dotenv import load_dotenv

load_dotenv()

PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')

PAYPAL_API_BASE = 'https://api-m.sandbox.paypal.com' if PAYPAL_MODE == 'sandbox' else 'https://api-m.paypal.com'

def get_paypal_access_token():
    auth = (PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
    headers = {'Accept': 'application/json', 'Accept-Language': 'en_US'}
    data = {'grant_type': 'client_credentials'}
    resp = requests.post(f'{PAYPAL_API_BASE}/v1/oauth2/token', headers=headers, data=data, auth=auth)
    resp.raise_for_status()
    return resp.json()['access_token']

def create_paypal_order(amount, description):
    token = get_paypal_access_token()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    data = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'amount': {'currency_code': 'USD', 'value': str(amount)},
            'description': description
        }]
    }
    resp = requests.post(f'{PAYPAL_API_BASE}/v2/checkout/orders', json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()
