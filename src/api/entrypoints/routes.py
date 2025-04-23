from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Literal
import os

from addons.integration.plugins.capsule import CapsulePlugin
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
    TokenRefreshError,
    APIRequestError,
    InvalidStateError,
    TokenRevocationError,
)


router = APIRouter(prefix="/integrations", tags=["Integrations"])
settings = AppSettings()


def get_capsule_plugin() -> CapsulePlugin:
    return CapsulePlugin()


@router.get("/authorization-url")
def get_authorization_url(
    pm: AnnotatedPluginManager,
    settings: AnnotatedSettings,
    name: Literal["copper", "capsule"] | None = None,
):
    try:
        session = {}
        return pm.hook.get_auth_url(settings=settings.auth, session=session)
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/callback")
def handle_oauth_callback(
    code: str,
    state: str,
    settings: AnnotatedSettings,
    plugin: CapsulePlugin = Depends(get_capsule_plugin),
):
    try:
        token_response = plugin.handle_callback(
            {"code": code, "state": state, "session": {"oauth_state": state}}
        )
        save_tokens_to_json(token_response)
        return {"access_token_response": token_response}
    except InvalidStateError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    except TokenExchangeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OAuthError as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@router.get("/contacts")
def fetch_contacts(
    request: Request, plugin: CapsulePlugin = Depends(get_capsule_plugin)
):
    try:
        tokens = get_stored_tokens()
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="Authorization token missing or expired. Please re-authenticate.",
            )

        page = request.query_params.get("page", "1")
        try:
            page_num = int(page)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid page number. Must be an integer."
            )

        contacts = plugin.get_contacts(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            client_id=settings.auth.client_id,
            client_secret=settings.auth.client_secret,
            page=page_num,
        )

        save_contacts_to_json(contacts)
        return {"contacts": contacts}
    except APIRequestError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/revoke")
def revoke_tokens(plugin: CapsulePlugin = Depends(get_capsule_plugin)):
    try:
        tokens = get_stored_tokens()
        if not tokens:
            return {"message": "No active tokens to revoke"}

        refresh_success = True
        if "refresh_token" in tokens:
            refresh_success = plugin.revoke_token(
                tokens["refresh_token"], "refresh_token"
            )

        access_success = True
        if "access_token" in tokens:
            access_success = plugin.revoke_token(tokens["access_token"], "access_token")

        if not (refresh_success and access_success):
            raise TokenRevocationError("Failed to revoke one or more tokens")

        # Remove token file if exists
        file_removed = False
        if os.path.exists(TOKEN_FILE_PATH):
            try:
                os.remove(TOKEN_FILE_PATH)
                file_removed = True
            except OSError as e:
                raise TokenRevocationError(f"Failed to remove token file: {str(e)}")

        return {"message": "Tokens revoked successfully", "file_removed": file_removed}
    except TokenRevocationError as e:
        raise HTTPException(status_code=400, detail=str(e))
