import json
import random
import string
from typing import Any, Dict, Optional
from urllib.parse import urlencode
import requests
from datetime import datetime, timedelta
from config import settings
from config.settings import AppSettings
from addons.integration.hooks import hookimpl
from config.settings import AuthSettings
from addons.storage import save_tokens_to_json


settings = AppSettings()

def generate_state(session):
    state = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    session["oauth_state"] = state
    return state


class CapsulePlugin:
    @hookimpl
    def get_auth_url(self, settings: AuthSettings, session):
        base_uri = "https://api.capsulecrm.com/oauth/authorise"
        state = generate_state(session)

        params = {
            "response_type": "code",
            "client_id": settings.client_id,
            "redirect_uri": "http://localhost:8000/integration/callback",
            "scope": "read write",
            "state": state,
        }
        query_string = urlencode(params)
        full_uri = f"{base_uri}?{query_string}"
        return full_uri


def handle_callback(request, client_id, client_secret):
    code = request.args.get("code")
    received_state = request.args.get("state")
    stored_state = request.session.get("oauth_state")

    if received_state != stored_state:
        print("State mismatch!")
        return None

    return exchange_token(code, client_id, client_secret)

def exchange_token(code: str, client_id: str, client_secret: str):
    url = "https://api.capsulecrm.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "http://localhost:8000/integration/callback",  
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=data, headers=headers)
        
        # Add detailed error logging
        if response.status_code != 200:
            error_detail = response.json()
            print(f"Token exchange failed. Error details: {error_detail}")
            print(f"Request data sent: {data}")
            response.raise_for_status()
            
        token_data = response.json()
        return token_data
    except Exception as e:
        print(f"Full error during token exchange: {str(e)}")
        return None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Refresh access token using refresh token."""
    url = "https://api.capsulecrm.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.auth.client_id,
        "client_secret": settings.auth.client_secret
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        
        # Calculate expiration time
        expires_in = token_data.get("expires_in", 3600)  # default 1 hour if not provided
        token_data["expires_at"] = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
        
        return token_data
    except requests.RequestException as e:
        print(f"Failed to refresh token: {e}")
        return None

def get_contacts(
    access_token: str,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    page: int = 1,
):
    url = f"https://api.capsulecrm.com/api/v2/parties?page={page}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        new_tokens = refresh_access_token(refresh_token)
        if new_tokens and "access_token" in new_tokens:
            save_tokens_to_json(new_tokens)
            headers["Authorization"] = f"Bearer {new_tokens['access_token']}"
            retry_response = requests.get(url, headers=headers)
            return retry_response.json() if retry_response.status_code == 200 else {"error": "Failed retry"}
        else:
            return {"error": "Token expired and refresh failed"}
    else:
        return {"error": response.text}

