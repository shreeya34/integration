import json
import random
import string
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlencode

import requests
from requests.exceptions import RequestException

from config import settings
from config.settings import AppSettings
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





class CRMPlugin:
    @staticmethod
    def _generate_state() -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=32))

    def get_auth_url(self, crm_name: str) -> str:
        # settings = AppSettings()
        crm_settings = settings.crms.get(crm_name.lower())
        
        if not crm_settings:
            available_crms = list(settings.crms.keys())
            raise Exception(f"CRM '{crm_name}' not configured. Available CRMs: {available_crms}")

        params = {
            "response_type": "code",
            "client_id": crm_settings.client_id,
            "redirect_uri": f"http://localhost:8000{crm_settings.config.redirect_path}",
            "scope": crm_settings.config.scope,
            "state": self._generate_state(), 
            "access_type": "offline", 
            "prompt": "consent" 
        }
        
        return f"{crm_settings.config.auth_url}?{urlencode(params)}"
    
    @hookimpl
    def exchange_token(self, crm_name: str, code: str) -> Dict:
        crm_settings = settings.crms.get(crm_name.lower())
        if not crm_settings:
            raise OAuthError(f"CRM '{crm_name}' not configured")

        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": crm_settings.client_id,
                "client_secret": crm_settings.client_secret,
                "redirect_uri": f"http://localhost:8000{crm_settings.config.redirect_path}",
            }

            response = requests.post(
                crm_settings.config.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise TokenExchangeError(
                    f"Token exchange failed with status {response.status_code}: {error_data.get('error', 'Unknown error')}"
                )
            token_data = response.json()
            token_data["crm_name"] = crm_name.lower()
            return token_data
        except RequestException as e:
            raise TokenExchangeError(f"Token exchange request failed: {str(e)}")
        except json.JSONDecodeError:
            raise TokenExchangeError("Invalid JSON response from token endpoint")
    

    @hookimpl
    def refresh_access_token(self, crm_name: str, refresh_token: str) -> Dict:
        crm_settings = settings.crms.get(crm_name.lower())
        if not crm_settings:
            raise OAuthError(f"CRM '{crm_name}' not configured")

        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": crm_settings.client_id,
                "client_secret": crm_settings.client_secret,
            }

            response = requests.post(
                crm_settings.config.token_url,
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
            token_data["crm_name"] = crm_name.lower()  # Add CRM name to the token data
            return token_data
        except RequestException as e:
            raise TokenRefreshError(f"Token refresh request failed: {str(e)}")
        except json.JSONDecodeError:
            raise TokenRefreshError("Invalid JSON response from token endpoint")
   

       
    @hookimpl
    def get_contacts(
        self,
        crm_name: str,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        page: int = 1,
    ) -> Dict:
        try:
            crm_settings = settings.crms.get(crm_name.lower())
            if not crm_settings:
                raise APIRequestError(f"CRM '{crm_name}' not configured")
            
            if crm_name.lower() == "capsule":
                url = f"https://api.capsulecrm.com/api/v2/parties?page={page}"
            elif crm_name.lower() == "zoho":
                url = f"https://www.zohoapis.com/crm/v2/Contacts?page={page}"
            else:
                raise APIRequestError(f"Unsupported CRM: {crm_name}")
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()

            if response.status_code == 401:
                new_tokens = self.refresh_access_token(crm_name, refresh_token)
                save_tokens_to_json(new_tokens, crm_name)
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
    # @hookimpl
    # def revoke_token(self, token: str, token_type_hint: str = "refresh_token") -> bool:
    #     try:
    #         data = {
    #             "token": token,
    #             "token_type_hint": token_type_hint,
    #             "client_id": settings.auth.client_id,
    #             "client_secret": settings.auth.client_secret,
    #         }

    #         response = requests.post(
    #             "https://api.capsulecrm.com/oauth/token/revoke",
    #             data=data,
    #             headers={"Content-Type": "application/x-www-form-urlencoded"},
    #             timeout=30,
    #         )

    #         if response.status_code != 200:
    #             raise TokenRevocationError(
    #                 f"Token revocation failed with status {response.status_code}"
    #             )
    #         return True
    #     except RequestException as e:
    #         raise TokenRevocationError(f"Token revocation request failed: {str(e)}")
