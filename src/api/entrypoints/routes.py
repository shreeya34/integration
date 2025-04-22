import os
from typing import Literal
from fastapi import APIRouter, Request
from addons.integration.plugins.capsule import get_contacts
from addons.storage import TOKEN_FILE_PATH, get_stored_tokens, save_contacts_to_json
from api.dependency import AnnotatedPluginManager, AnnotatedSettings
from addons.integration.plugins.capsule import exchange_token
from config import settings
from config.settings import AppSettings

settings = AppSettings()

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("/authorization-url")
def get_authorization_url_resource(
    pm: AnnotatedPluginManager,
    settings: AnnotatedSettings,
    name: Literal["copper", "capsule"] | None = None,
):
    session = {}
    return pm.hook.get_auth_url(settings=settings.auth, session=session)
@router.get("/callback")
def generate_access_token(
    code: str,
    state: str,
    settings: AnnotatedSettings,
):
    token_response = exchange_token(
        code=code,
        client_id=settings.auth.client_id,
        client_secret=settings.auth.client_secret,
    )

    if token_response:
        from addons.storage import save_tokens_to_json
        save_tokens_to_json(token_response)
        return {"access_token_response": token_response}
    else:
        return {"error": "Failed to fetch access token"}


@router.get("/contacts")
def get_contacts_api(req: Request):
    tokens = get_stored_tokens()
    if not tokens:
        return {"error": "Authorization token missing or expired. Please re-authenticate."}

    page_num = req.query_params.get("page", 1)
    
    contacts = get_contacts(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        client_id=settings.auth.client_id,
        client_secret=settings.auth.client_secret,
        page=int(page_num)
    )

    if "error" in contacts:
        return {"error": contacts["error"]}

    save_contacts_to_json(contacts)
    return {"contacts": contacts}


# @router.post("/revoke")
# def revoke_tokens():
#     """
#     Revoke both access and refresh tokens and remove them from local storage
#     """
#     # Get current tokens
#     tokens = get_stored_tokens()
#     if not tokens:
#         return {"message": "No active tokens to revoke"}

#     # Revoke both tokens
#     from addons.integration.plugins.capsule import revoke_token
    
#     # Revoke refresh token first
#     if 'refresh_token' in tokens:
#         revoke_token(tokens['refresh_token'], "refresh_token")
    
#     # Then revoke access token
#     if 'access_token' in tokens:
#         revoke_token(tokens['access_token'], "access_token")

#     try:
#         if os.path.exists(TOKEN_FILE_PATH):
#             os.remove(TOKEN_FILE_PATH)
#             return {"message": "Tokens revoked and removed successfully"}
#         return {"message": "Tokens revoked but no local file found"}
#     except Exception as e:
#         return {"error": f"Failed to remove token file: {str(e)}"}