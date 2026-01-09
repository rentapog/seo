import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
CLOUDFLARE_ZONE_ID = os.getenv('CLOUDFLARE_ZONE_ID')
CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')

headers = {
    'Authorization': f'Bearer {CLOUDFLARE_API_TOKEN}',
    'Content-Type': 'application/json',
}

def list_dns_records():
    url = f'https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records'
    resp = requests.get(url, headers=headers)
    print('DNS Records:', resp.json())

def create_dns_record(type, name, content):
    url = f'https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records'
    data = {
        'type': type,
        'name': name,
        'content': content,
        'ttl': 1,
        'proxied': False
    }
    resp = requests.post(url, headers=headers, json=data)
    print('Create Record:', resp.json())

if __name__ == "__main__":
    list_dns_records()
    # Example: create_dns_record('A', 'test.seobrainai.com', '1.2.3.4')
