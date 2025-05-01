from typing import Dict, List, Optional, Union
from fastapi import APIRouter, Depends, Query, Request, HTTPException,status
from pluggy import PluginManager
import pluggy
from addons.integration.hookspec import Spec, get_plugin_manager
from addons.integration.plugins.zoho import ZohoCRMPlugin
from addons.integration.plugins.capsule import CapsuleCRMPlugin
from addons.storage import (
    get_stored_tokens,
    save_contacts_to_json,
    save_tokens_to_json,
    get_state,
)
from api.dependency import AnnotatedPluginManager, AnnotatedSettings
from config.settings import AppSettings
from core.exception import (
    CRMIntegrationError,
    ContactsFetchError,
    InvalidPageNumberError,
    InvalidStateError,
    OAuthError,
    TokenExchangeError,
    UnsupportedCRMError,
)
import os
from addons.integration.crm_enum import CRMName  
from api.utils.logger import get_logger

logger = get_logger()


router = APIRouter(prefix="/integrations", tags=["Integrations"])



def get_plugin(crm_name: str):
        return CRMName.get_plugin(crm_name)
    
    




@router.get("/authorization-url")
def get_authorization_url_resource(
    pm: AnnotatedPluginManager,
    settings: AnnotatedSettings,
    crm_name: Optional[List[str]] = Query(default=None, alias="crm_name")
):
    if not crm_name:
        # Call all plugins
        plugin_results = pm.hook.get_auth_url(settings=settings)
    else:
        # Filter to matching plugins
        matching_plugins = [
            impl.plugin
            for impl in pm.hook.get_auth_url.get_hookimpls()
            if getattr(impl.plugin, "crm_name", None) in crm_name
        ]

        if not matching_plugins:
            logger.warning(f"CRM plugin not found for integration crm_name(s): {crm_name}")
            raise UnsupportedCRMError(
                message=f"No plugins found for integration(s): {crm_name}",
                status_code=404,
            )

        # Use only the selected plugins
        subset = pm.subset_hook_caller(
            "get_auth_url",
            remove_plugins=[
                plugin for plugin in pm.get_plugins() if plugin not in matching_plugins
            ]
        )
        plugin_results = subset(settings=settings)

    # Safely merge plugin outputs
    merged_plugins: Dict[str, str] = {}
    for plugin_result in plugin_results:
        if isinstance(plugin_result, dict):
            merged_plugins.update(plugin_result)
        else:
            logger.warning(f"Expected dict from plugin, got: {type(plugin_result)} - {plugin_result}")

    logger.info(f"Authentication URLs requested for integrations: {crm_name or 'all'}")
    return merged_plugins

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
    
    # Prepare the response data
    response_data = {
        "status": "success",
        "crm": crm_name.lower(),
        "contacts": contacts.get("data", []),
        "pagination": {
            "page": contacts.get("page", 1),
            "total": contacts.get("total", 0)
        },
        "message": f"Contacts fetched from {crm_name} CRM"
    }

    filepath = save_contacts_to_json(response_data, crm_name=crm_name)
    
    response_data["message"] = f"Contacts fetched from {crm_name} CRM and saved to {os.path.basename(filepath)}"
    
    return response_data