import json
import random
import string
from datetime import datetime, timedelta
from urllib.parse import urlencode
import requests
from requests.exceptions import RequestException
from config import settings
from core.exception import (
    OAuthError,
    TokenRefreshError,
    TokenExchangeError,
    APIRequestError
)
settings = settings.AppSettings()
class ZohoCRMPlugin:
    def __init__(self):
        self.crm_name = "zoho"
        self.crm_settings = settings.crms.get(self.crm_name)
        if not self.crm_settings:
            raise OAuthError(f"Zoho CRM not configured")

    def _generate_state(self) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=32))

    def get_auth_url(self) -> str:
        params = {
            "response_type": "code",
            "client_id": self.crm_settings.client_id,
            "redirect_uri": f"http://localhost:8000{self.crm_settings.config.redirect_path}",
            "scope": self.crm_settings.config.scope,
            "state": self._generate_state(),
            "access_type": "offline",
            "prompt": "consent"
        }
        return f"{self.crm_settings.config.auth_url}?{urlencode(params)}"

    def exchange_token(self, code: str) -> dict:
        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.crm_settings.client_id,
                "client_secret": self.crm_settings.client_secret,
                "redirect_uri": f"http://localhost:8000{self.crm_settings.config.redirect_path}",
            }

            response = requests.post(
                self.crm_settings.config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise TokenExchangeError(
                    f"Token exchange failed: {error_data.get('error', 'Unknown error')}"
                )

            token_data = response.json()
            token_data["crm_name"] = self.crm_name
            return token_data
        except RequestException as e:
            raise TokenExchangeError(f"Token exchange request failed: {str(e)}")

    def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.crm_settings.client_id,
                "client_secret": self.crm_settings.client_secret,
            }

            response = requests.post(
                self.crm_settings.config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise TokenRefreshError(
                    f"Token refresh failed: {error_data.get('error', 'Unknown error')}"
                )

            token_data = response.json()
            token_data["expires_at"] = (
                datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
            ).isoformat()
            token_data["crm_name"] = self.crm_name
            return token_data
        except RequestException as e:
            raise TokenRefreshError(f"Token refresh request failed: {str(e)}")

    def get_contacts(self, access_token: str, refresh_token: str, page: int = 1) -> dict:
        try:
            url = f"https://www.zohoapis.com/crm/v2/Contacts?page={page}"
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Accept": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 401:
                new_tokens = self.refresh_access_token(refresh_token)
                headers["Authorization"] = f"Zoho-oauthtoken {new_tokens['access_token']}"
                retry_response = requests.get(url, headers=headers, timeout=30)

                if retry_response.status_code == 200:
                    return retry_response.json()
                raise APIRequestError("Failed after token refresh")

            raise APIRequestError(f"Failed with status {response.status_code}")
        except RequestException as e:
            raise APIRequestError(f"Request failed: {str(e)}")