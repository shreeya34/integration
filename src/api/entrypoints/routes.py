from typing import Optional
from fastapi import APIRouter, Path, Request, HTTPException,status
from addons.integration.plugins.zoho import ZohoCRMPlugin
from addons.integration.plugins.capsule import CapsuleCRMPlugin
from addons.storage import (
    get_stored_tokens,
    save_contacts_to_json,
    save_tokens_to_json,
    get_state,
)
from core.exception import (
    CRMIntegrationError,
    ContactsFetchError,
    InvalidPageNumberError,
    InvalidStateError,
    OAuthError,
    TokenExchangeError,
    UnsupportedCRMError,
)
from addons.integration.crm_enum import CRMName  

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def get_plugin(crm_name: str):
    try:
        return CRMName.get_plugin(crm_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/authorization-url")
def get_auth_urls(crm_name: Optional[str] = None):
    try:
        if crm_name is None:
            return {
                crm.value: get_plugin(crm.value).get_auth_url()
                for crm in CRMName
            }
        
        plugin = get_plugin(crm_name)
        return {"crm": crm_name, "auth_url": plugin.get_auth_url()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/callback/{crm_name}")
def oauth_callback(crm_name: str, code: str, state: str):
    try:
        stored_state = get_state(crm_name)
        if not stored_state or stored_state != state:
            raise InvalidStateError("Invalid state parameter", 400)

        plugin = get_plugin(crm_name)
        token_response = plugin.exchange_token(code)
        save_tokens_to_json(token_response, crm_name)
        
        return {"status": "success", "crm": crm_name, **token_response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh-token/{crm_name}")
def refresh_token(crm_name: str, refresh_token: str):
    try:
        plugin = get_plugin(crm_name)
        token_response = plugin.refresh_access_token(refresh_token)
        save_tokens_to_json(token_response, crm_name)
        return {"status": "success", **token_response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/contacts")
def fetch_contacts(request: Request):
        tokens = get_stored_tokens()
        if not tokens:
            raise OAuthError(
                detail="Authorization required. Please authenticate with a CRM first.",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        crm_name = tokens.get("crm_name")
        if not crm_name:
            raise CRMIntegrationError(
                detail="Could not determine CRM from stored tokens.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        if not access_token or not refresh_token:
            raise TokenExchangeError(
                detail="Invalid token format. Missing required tokens.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            page = int(request.query_params.get("page", 1))
            if page < 1:
                raise InvalidPageNumberError(detail="Page number must be positive")
        except ValueError:
            raise InvalidPageNumberError()

        try:
            plugin = get_plugin(crm_name.lower())
        except Exception as e:
            raise UnsupportedCRMError(
                crm_name=crm_name,
                detail=f"Failed to initialize CRM plugin: {str(e)}"
            )

        try:
            contacts = plugin.get_contacts(
                access_token=access_token,
                refresh_token=refresh_token,
                page=page
            )
        except Exception as e:
            raise ContactsFetchError(
                detail=f"Failed to fetch contacts from {crm_name}: {str(e)}",
                crm_name=crm_name,
                page=page
            )

        try:
            if crm_name.lower() == "zoho":
                transformed_contacts = {"parties": contacts.get("data", [])}
                save_contacts_to_json(transformed_contacts, f"{crm_name}_contacts.json")
            else:
                save_contacts_to_json(contacts, f"{crm_name}_contacts.json")
        except Exception as e:
            raise CRMIntegrationError(
                detail=f"Failed to save contacts: {str(e)}",
                operation="contact_save"
            )

        return {
            "status": "success",
            "crm": crm_name.lower(),
            "contacts": contacts,
            "message": f"Contacts fetched from {crm_name} CRM",
        }


 