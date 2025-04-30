import random
import string
from datetime import datetime, timedelta
from urllib.parse import urlencode
import httpx
from addons.integration.hooks import hookimpl
from addons.storage import get_state, save_state
from config import settings
from core.exception import (
    InvalidStateError,
    OAuthError,
    TokenRefreshError,
    TokenExchangeError,
    APIRequestError,
)
from api.utils.logger import get_logger

logger = get_logger()

settings = settings.AppSettings()


class CapsuleCRMPlugin:
    def __init__(self):
        self.crm_name = "capsule"
        self.crm_settings = settings.crms.get(self.crm_name)
        if not self.crm_settings:
            logger.error("Capsule CRM configuration not found.")
            raise OAuthError("Capsule CRM not configured")
        logger.info("CapsuleCRMPlugin initialized successfully.")

    def _generate_random_value(self) -> str:
        state = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        save_state(state, self.crm_name)
        logger.debug(f"Generated and saved state: {state}")
        return state

    @hookimpl
    def get_auth_url(self) -> str:
        state = self._generate_random_value()
        params = {
            "response_type": "code",
            "client_id": self.crm_settings.client_id,
            "redirect_uri": f"http://localhost:8000{self.crm_settings.config.redirect_path}",
            "scope": self.crm_settings.config.scope,
            "state": state,
        }
        auth_url = f"{self.crm_settings.config.auth_url}?{urlencode(params)}"
        logger.info(f"Generated auth URL: {auth_url}")
        return auth_url

    @hookimpl
    def exchange_token(self, code: str, state: str = None) -> dict:
        if state:
            stored_state = get_state(self.crm_name)
            if not stored_state or stored_state != state:
                logger.warning("State verification failed.")
                raise InvalidStateError("State verification failed", status_code=400)
            logger.info("State verified successfully.")

        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.crm_settings.client_id,
                "client_secret": self.crm_settings.client_secret,
                "redirect_uri": f"http://localhost:8000{self.crm_settings.config.redirect_path}",
            }

            with httpx.Client(timeout=30) as client:
                response = client.post(
                    self.crm_settings.config.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Token exchange failed: {error_data}")
                raise TokenExchangeError(
                    f"Token exchange failed: {error_data.get('error', 'Unknown error')}"
                )

            token_data = response.json()
            token_data["crm_name"] = self.crm_name
            logger.info("Token exchanged successfully.")
            return token_data
        except httpx.HTTPError as e:
            logger.exception("Token exchange request failed.")
            raise TokenExchangeError(f"Token exchange request failed: {str(e)}")

    @hookimpl
    def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.crm_settings.client_id,
                "client_secret": self.crm_settings.client_secret,
            }

            with httpx.Client(timeout=30) as client:
                response = client.post(
                    self.crm_settings.config.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Token refresh failed: {error_data}")
                raise TokenRefreshError(
                    f"Token refresh failed: {error_data.get('error', 'Unknown error')}"
                )

            token_data = response.json()
            token_data["expires_at"] = (
                datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
            ).isoformat()
            token_data["crm_name"] = self.crm_name
            logger.info("Access token refreshed successfully.")
            return token_data
        except httpx.HTTPError as e:
            logger.exception("Token refresh request failed.")
            raise TokenRefreshError(f"Token refresh request failed: {str(e)}")

    @hookimpl
    def get_contacts(self, access_token: str, refresh_token: str, page: int = 1) -> dict:
        url = f"https://api.capsulecrm.com/api/v2/parties?page={page}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=headers)

                if response.status_code == 200:
                    logger.info(f"Fetched contacts page {page} successfully.")
                    return response.json()

                if response.status_code == 401:
                    logger.warning("Access token expired, attempting refresh.")
                    new_tokens = self.refresh_access_token(refresh_token)
                    headers["Authorization"] = f"Bearer {new_tokens['access_token']}"
                    retry_response = client.get(url, headers=headers)

                    if retry_response.status_code == 200:
                        logger.info(f"Fetched contacts page {page} after token refresh.")
                        return retry_response.json()

                    logger.error("Failed to fetch contacts even after token refresh.")
                    raise APIRequestError("Failed after token refresh")

                logger.error(f"Failed to fetch contacts, status code: {response.status_code}")
                raise APIRequestError(f"Failed with status {response.status_code}")
        except httpx.HTTPError as e:
            logger.exception("Request to fetch contacts failed.")
            raise APIRequestError(f"Request failed: {str(e)}")
