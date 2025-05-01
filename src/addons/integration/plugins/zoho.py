import json
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Union
from urllib.parse import urlencode
import httpx
from httpx import HTTPError

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

class ZohoCRMPlugin:
    def __init__(self):
        self.crm_name = "zoho"
        self.crm_settings = settings.crms.get(self.crm_name)
        if not self.crm_settings:
            logger.error("Zoho CRM not configured")
            raise OAuthError("Zoho CRM not configured")
        logger.info("ZohoCRMPlugin initialized successfully")

    def _generate_random_value(self) -> str:
        state = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        save_state(state, self.crm_name)
        logger.debug(f"Generated state: {state}")
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
            "access_type": "offline",
            "prompt": "consent",
        }
        auth_url = f"{self.crm_settings.config.auth_url}?{urlencode(params)}"
        logger.info("Generated auth URL")
        return auth_url

    @hookimpl
    def exchange_token(self, code: str, state: str = None) -> dict:
        if state:
            stored_state = get_state(self.crm_name)
            if not stored_state or stored_state != state:
                logger.warning("Invalid state parameter")
                raise InvalidStateError(status_code=400, detail="Invalid state parameter")
            logger.info("State verified successfully")

        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.crm_settings.client_id,
                "client_secret": self.crm_settings.client_secret,
                "redirect_uri": f"http://localhost:8000{self.crm_settings.config.redirect_path}",
            }

            response = httpx.post(
                self.crm_settings.config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Token exchange failed: {error_data}")
                raise TokenExchangeError("Token exchange failed")
            token_data = response.json()
            logger.info("Token exchanged successfully")
            return token_data
        except HTTPError as e:
            logger.exception("Token exchange request failed")
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

            response = httpx.post(
                self.crm_settings.config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Token refresh failed: {error_data}")
                raise TokenRefreshError("Token refresh failed")
            token_data = response.json()
            logger.info("Access token refreshed successfully")
            return token_data
        except HTTPError as e:
            logger.exception("Token refresh request failed")
            raise TokenRefreshError(f"Token refresh request failed: {str(e)}")
    @hookimpl
    def filter_contacts(self, contacts: Union[List, Dict]) -> List[Dict]:
        """Filter and standardize Zoho CRM contact data with guaranteed field extraction"""
        # Handle different input formats
        if isinstance(contacts, dict):
            contact_list = contacts.get('data', [contacts])
        else:
            contact_list = contacts if isinstance(contacts, list) else [contacts]

        standardized_contacts = []
        for contact in contact_list:
            if not isinstance(contact, dict):
                continue

            # Extract all possible field variations (case-insensitive)
            def get_field(data, *keys):
                for key in keys:
                    if key in data:
                        return data[key]
                    # Try case-insensitive match
                    lower_key = key.lower()
                    for k, v in data.items():
                        if k.lower() == lower_key:
                            return v
                return ""

            # Build the standardized contact
            standardized = {
                "id": str(get_field(contact, "id")),
                "first_name": get_field(contact, "First_Name", "first_name"),
                "last_name": get_field(contact, "Last_Name", "last_name"),
                "name": get_field(contact, "Full_Name", "full_name") or 
                    f"{get_field(contact, 'First_Name', 'first_name')} {get_field(contact, 'Last_Name', 'last_name')}".strip(),
                "email": get_field(contact, "Email", "email"),
                "phone": get_field(contact, "Phone", "phone"),
                "mobile": get_field(contact, "Mobile", "mobile", "Other_Phone", "other_phone"),
            }
            
            # Add owner email if available
            owner_data = contact.get("Owner", {})
            if isinstance(owner_data, dict):
                standardized["owner_email"] = owner_data.get("email", "")

            standardized_contacts.append(standardized)

        return standardized_contacts

    @hookimpl
    def get_contacts(self, access_token: str, refresh_token: str, page: int = 1) -> dict:
        try:
            url = f"https://www.zohoapis.com/crm/v2/Contacts?page={page}"
            headers = {
                "Authorization": f"Zoho-oauthtoken {access_token}",
                "Accept": "application/json",
            }

            response = httpx.get(url, headers=headers, timeout=30.0)
            if response.status_code == 200:
                logger.info(f"Fetched contacts page {page} successfully")
                raw_data = response.json()
                
                # Extract the contacts array from the Zoho response
                contacts_data = raw_data.get("data", [])
                
                filtered_contacts = self.filter_contacts(contacts_data)
                return {
                    "data": filtered_contacts,
                    "page": page,
                    "total": raw_data.get("info", {}).get("count", len(filtered_contacts))
                }
                
            if response.status_code == 401:
                logger.warning("Access token expired, attempting refresh")
                new_tokens = self.refresh_access_token(refresh_token)
                headers["Authorization"] = f"Zoho-oauthtoken {new_tokens['access_token']}"
                retry_response = httpx.get(url, headers=headers, timeout=30.0)
                if retry_response.status_code == 200:
                    logger.info("Fetched contacts after token refresh")
                    raw_data = retry_response.json()
                    contacts_data = raw_data.get("data", [])
                    filtered_contacts = self.filter_contacts(contacts_data)
                    return {
                        "data": filtered_contacts,
                        "page": page,
                        "total": raw_data.get("info", {}).get("count", len(filtered_contacts)),
                        "access_token": new_tokens['access_token']  # Return the new token
                    }
                logger.error("Failed to fetch contacts after token refresh")
                raise APIRequestError("Failed after token refresh")
                
            logger.error(f"Failed to fetch contacts: Status {response.status_code}")
            raise APIRequestError(f"Failed with status {response.status_code}")
        except HTTPError as e:
            logger.exception("Contact request failed")
            raise APIRequestError(f"Request failed: {str(e)}")