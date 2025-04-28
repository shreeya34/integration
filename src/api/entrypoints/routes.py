from fastapi import APIRouter, Request, HTTPException
from addons.integration.plugins.zoho import ZohoCRMPlugin
from addons.integration.plugins.capsule import CapsuleCRMPlugin
from addons.storage import (
    get_stored_tokens,
    save_contacts_to_json,
    save_tokens_to_json,
    get_state,
)
from core.exception import InvalidStateError

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def get_plugin(crm_name: str):
    crm_name = crm_name.lower()
    if crm_name == "zoho":
        return ZohoCRMPlugin()
    elif crm_name == "capsule":
        return CapsuleCRMPlugin()
    raise HTTPException(status_code=400, detail=f"Unsupported CRM: {crm_name}")


@router.get("/authorization-url/{crm_name}")
def get_authorization_url(crm_name: str):
    try:
        plugin = get_plugin(crm_name)
        auth_url = plugin.get_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback/{crm_name}")
def oauth_callback(crm_name: str, code: str, state: str):
    try:
        stored_state = get_state(crm_name)

        if not stored_state:
            raise InvalidStateError("No state found", 400)

        if stored_state != state:
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
    try:
        tokens = get_stored_tokens()
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="Authorization required. Please authenticate with a CRM first.",
            )

        crm_name = tokens.get("crm_name")
        if not crm_name:
            raise HTTPException(
                status_code=400, detail="Could not determine CRM from stored tokens."
            )

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        if not access_token or not refresh_token:
            raise HTTPException(
                status_code=400, detail="Invalid token format. Missing required tokens."
            )

        try:
            page = int(request.query_params.get("page", 1))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid page number")

        plugin = get_plugin(crm_name.lower())

        contacts = plugin.get_contacts(
            access_token=access_token, refresh_token=refresh_token, page=page
        )

        save_contacts_to_json(contacts, f"{crm_name}_contacts.json")

        return {
            "status": "success",
            "crm": crm_name.lower(),
            "contacts": contacts,
            "message": f"Contacts fetched from {crm_name} CRM",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch contacts: {str(e)}"
        )
