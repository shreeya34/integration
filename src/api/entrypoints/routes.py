from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Literal
import os
import pluggy
from addons.integration.plugins.capsule import  CRMPlugin
from addons.storage import (
    TOKEN_FILE_PATH,
    get_stored_tokens,
    save_contacts_to_json,
    save_tokens_to_json,
)
from api.dependency import AnnotatedPluginManager, AnnotatedSettings
from config.settings import AppSettings
from core.exception import (
    OAuthError,
    TokenExchangeError,
    APIRequestError,
    InvalidStateError,
    TokenRevocationError,
)


router = APIRouter(prefix="/integrations", tags=["Integrations"])
settings = AppSettings()

from fastapi import APIRouter, Request, HTTPException
from config.settings import AppSettings

router = APIRouter(prefix="/integrations", tags=["Integrations"])

settings = AppSettings()

plugin = CRMPlugin()

@router.get("/authorization-url/{crm_name}")
def get_authorization_url(
    crm_name: str,
    request: Request, 
):
    try:
        plugin = CRMPlugin()
        return plugin.get_auth_url(crm_name.lower())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/callback/{crm_name}")
def oauth_callback(
    crm_name: str,
    code: str,
    state: str,
):
    try:
        token_response = plugin.exchange_token(crm_name.lower(), code)
        
        save_tokens_to_json(token_response,crm_name)
        
        return {
            "status": "success",
            "access_token": token_response.get("access_token"),
            "refresh_token": token_response.get("refresh_token"),
            "expires_in": token_response.get("expires_in")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/refresh-token/{crm_name}")
def refresh_token(
    crm_name: str,
    refresh_token: str
):
    try:
        token_response = plugin.refresh_access_token(crm_name.lower(), refresh_token)
        save_tokens_to_json(token_response,crm_name)
        
        return {
            "status": "success",
            "access_token": token_response.get("access_token"),
            "expires_in": token_response.get("expires_in")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/contacts")
def fetch_contacts(
    request: Request, 
):
    try:
        
        tokens = get_stored_tokens()
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="Authorization token missing or expired. Please re-authenticate.",
            )
            
        crm_name = tokens.get("crm_name")
        if not crm_name:
            raise HTTPException(
                status_code=400,
                detail="No CRM associated with this name",
            )
            
        page = request.query_params.get("page", "1")
        try:
            page_num = int(page)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid page number. Must be an integer."
            )

        contacts = plugin.get_contacts(
            crm_name=crm_name,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            client_id=settings.crms[crm_name].client_id,
            client_secret=settings.crms[crm_name].client_secret,
            page=page_num,
        )

        save_contacts_to_json(contacts)
        return {"contacts": contacts, "crm": crm_name}
    except APIRequestError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


# @router.post("/revoke")
# def revoke_tokens(plugin: CapsulePlugin = Depends(get_capsule_plugin)):
#     try:
#         tokens = get_stored_tokens()
#         if not tokens:
#             return {"message": "No active tokens to revoke"}

#         refresh_success = True
#         if "refresh_token" in tokens:
#             refresh_success = plugin.revoke_token(
#                 tokens["refresh_token"], "refresh_token"
#             )

#         access_success = True
#         if "access_token" in tokens:
#             access_success = plugin.revoke_token(tokens["access_token"], "access_token")

#         if not (refresh_success and access_success):
#             raise TokenRevocationError("Failed to revoke one or more tokens")

#         # Remove token file if exists
#         file_removed = False
#         if os.path.exists(TOKEN_FILE_PATH):
#             try:
#                 os.remove(TOKEN_FILE_PATH)
#                 file_removed = True
#             except OSError as e:
#                 raise TokenRevocationError(f"Failed to remove token file: {str(e)}")

#         return {"message": "Tokens revoked successfully", "file_removed": file_removed}
#     except TokenRevocationError as e:
#         raise HTTPException(status_code=400, detail=str(e))
