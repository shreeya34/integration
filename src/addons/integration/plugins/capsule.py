import json
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlencode

import requests
from requests.exceptions import RequestException

from config import settings
from config.settings import AppSettings, AuthSettings
from addons.integration.hooks import hookimpl
from addons.storage import save_tokens_to_json
from core.exception import (
    OAuthError,
    TokenRefreshError,
    InvalidStateError,
    TokenExchangeError,
    APIRequestError,
    TokenRevocationError,
)

settings = AppSettings()


class CapsulePlugin:
    @staticmethod
    def _generate_state() -> str:
        """Generate a random state for OAuth"""
        return "".join(random.choices(string.ascii_letters + string.digits, k=32))

    @hookimpl
    def get_auth_url(self, settings: AuthSettings, session: Dict) -> str:
        """Generate OAuth authorization URL"""
        try:
            params = {
                "response_type": "code",
                "client_id": settings.client_id,
                "redirect_uri": "http://localhost:8000/integration/callback",
                "scope": "read write",
                "state": self._generate_state(),
            }
            session["oauth_state"] = params["state"]
            return f"https://api.capsulecrm.com/oauth/authorise?{urlencode(params)}"
        except Exception as e:
            raise OAuthError(f"Failed to generate auth URL: {str(e)}")

    @hookimpl
    def handle_callback(self, request: Dict) -> Dict:
        try:
            code = request.get("code")
            received_state = request.get("state")
            stored_state = request.get("session", {}).get("oauth_state")

            if not code:
                raise OAuthError("Authorization code missing")
            if not received_state or not stored_state:
                raise OAuthError("State parameter missing")
            if received_state != stored_state:
                raise InvalidStateError()

            return self.exchange_token(
                code=code,
                client_id=settings.auth.client_id,
                client_secret=settings.auth.client_secret,
            )
        except Exception as e:
            raise OAuthError(f"Callback handling failed: {str(e)}")

    @hookimpl
    def exchange_token(self, code: str, client_id: str, client_secret: str) -> Dict:
        """Exchange authorization code for access token"""
        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": "http://localhost:8000/integration/callback",
            }

            response = requests.post(
                "https://api.capsulecrm.com/oauth/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise TokenExchangeError(
                    f"Token exchange failed with status {response.status_code}: {error_data.get('error', 'Unknown error')}"
                )

            return response.json()
        except RequestException as e:
            raise TokenExchangeError(f"Token exchange request failed: {str(e)}")
        except json.JSONDecodeError:
            raise TokenExchangeError("Invalid JSON response from token endpoint")

    @hookimpl
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh expired access token"""
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.auth.client_id,
                "client_secret": settings.auth.client_secret,
            }

            response = requests.post(
                "https://api.capsulecrm.com/oauth/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise TokenRefreshError(
                    f"Token refresh failed with status {response.status_code}: {error_data.get('error', 'Unknown error')}"
                )

            token_data = response.json()
            token_data["expires_at"] = (
                datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
            ).isoformat()
            return token_data
        except RequestException as e:
            raise TokenRefreshError(f"Token refresh request failed: {str(e)}")
        except json.JSONDecodeError:
            raise TokenRefreshError("Invalid JSON response from token endpoint")

    @hookimpl
    def get_contacts(
        self,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        page: int = 1,
    ) -> Dict:
        """Fetch contacts from CapsuleCRM"""
        try:
            url = f"https://api.capsulecrm.com/api/v2/parties?page={page}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 401:
                new_tokens = self.refresh_access_token(refresh_token)
                save_tokens_to_json(new_tokens)
                headers["Authorization"] = f"Bearer {new_tokens['access_token']}"
                retry_response = requests.get(url, headers=headers, timeout=30)

                if retry_response.status_code == 200:
                    return retry_response.json()
                raise APIRequestError(
                    "Failed to fetch contacts after token refresh",
                    status_code=retry_response.status_code,
                )

            raise APIRequestError(
                "Failed to fetch contacts", status_code=response.status_code
            )
        except RequestException as e:
            raise APIRequestError(f"Contacts API request failed: {str(e)}")

    @hookimpl
    def revoke_token(self, token: str, token_type_hint: str = "refresh_token") -> bool:
        try:
            data = {
                "token": token,
                "token_type_hint": token_type_hint,
                "client_id": settings.auth.client_id,
                "client_secret": settings.auth.client_secret,
            }

            response = requests.post(
                "https://api.capsulecrm.com/oauth/token/revoke",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

            if response.status_code != 200:
                raise TokenRevocationError(
                    f"Token revocation failed with status {response.status_code}"
                )
            return True
        except RequestException as e:
            raise TokenRevocationError(f"Token revocation request failed: {str(e)}")
