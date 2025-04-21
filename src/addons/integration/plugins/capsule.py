from addons.integration.hooks import hookimpl
from config.settings import AuthSettings
from urllib.parse import urlencode
import random
import string
import requests


def generate_state():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

class CapsulePlugin:
    @hookimpl
    def get_auth_url(self, settings: AuthSettings):
        base_uri = 'https://api.capsulecrm.com/oauth/authorise'
        params = {
            "response_type": "code",
            "client_id": settings.client_id,
            "redirect_uri": "http://localhost:8000/integration/callback",  
            "scope": "read write",
            "state": generate_state()  
        }
        query_string = urlencode(params)
        full_uri = f"{base_uri}?{query_string}"
        print(full_uri)
        return full_uri

def exchange_token(code: str, client_id: str, client_secret: str):
    url = "https://api.capsulecrm.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8000/integration/callback"
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(url, data=data, headers=headers)

    if response.status_code == 200:
        print("Access token response:", response.json())
        return response.json()
    else:
        print("Error:", response.text)
        return None



import requests

def get_contacts(access_token: str,page: int=1):
    url = f"https://api.capsulecrm.com/api/v2/parties?page={page}"
    
    headers = {
        "Authorization": access_token,
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()  
    elif response.status_code == 401:
        return {"error": "Unauthorized - Invalid or expired token"}
    else:
        return {"error": response.text}

