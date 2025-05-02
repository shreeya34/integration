from typing import Dict, List, Optional
from fastapi import APIRouter, Query, Request, HTTPException, status
from addons.storage import (
    get_stored_tokens,
    save_contacts_to_json,
    save_tokens_to_json,
    get_state,
)
from api.dependency import AnnotatedPluginManager, AnnotatedSettings
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
    logger.info(f"Fetching plugin for CRM: {crm_name}")
    return CRMName.get_plugin(crm_name)

@router.get("/authorization-url")
def get_authorization_url_resource(
    pm: AnnotatedPluginManager,
    settings: AnnotatedSettings,
    crm_name: Optional[List[str]] = Query(default=None, alias="crm_name")
):
    logger.info(f"Authorization URL requested for: {crm_name or 'all CRMs'}")
    if not crm_name:
        plugin_results = pm.hook.get_auth_url(settings=settings)
    else:
        matching_plugins = [
            impl.plugin
            for impl in pm.hook.get_auth_url.get_hookimpls()
            if getattr(impl.plugin, "crm_name", None) in crm_name
        ]

        if not matching_plugins:
            logger.warning(f"No matching CRM plugins found for: {crm_name}")
            raise UnsupportedCRMError(
                message=f"No plugins found for integration(s): {crm_name}",
                status_code=404,
            )

        subset = pm.subset_hook_caller(
            "get_auth_url",
            remove_plugins=[
                plugin for plugin in pm.get_plugins() if plugin not in matching_plugins
            ]
        )
        plugin_results = subset(settings=settings)

    merged_plugins: Dict[str, str] = {}
    for plugin_result in plugin_results:
        if isinstance(plugin_result, dict):
            merged_plugins.update(plugin_result)
        else:
            logger.warning(f"Expected dict from plugin, got: {type(plugin_result)} - {plugin_result}")

    logger.info(f"Successfully retrieved auth URLs: {merged_plugins}")
    return merged_plugins

@router.get("/callback/{crm_name}")
def oauth_callback(crm_name: str, code: str, state: str):
    logger.info(f"OAuth callback initiated for CRM: {crm_name}")
    try:
        stored_state = get_state(crm_name)
        if not stored_state or stored_state != state:
            logger.error("Invalid state parameter during OAuth callback")
            raise InvalidStateError("Invalid state parameter", 400)

        plugin = get_plugin(crm_name)
        token_response = plugin.exchange_token(code)
        save_tokens_to_json(token_response, crm_name)

        logger.info(f"OAuth token exchanged and saved for {crm_name}")
        return {"status": "success", "crm": crm_name, **token_response}
    except Exception as e:
        logger.exception(f"OAuth callback failed for {crm_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/refresh-token/{crm_name}")
def refresh_token(crm_name: str, refresh_token: str):
    logger.info(f"Token refresh initiated for CRM: {crm_name}")
    try:
        plugin = get_plugin(crm_name)
        token_response = plugin.refresh_access_token(refresh_token)
        save_tokens_to_json(token_response, crm_name)

        logger.info(f"Token refreshed successfully for {crm_name}")
        return {"status": "success", **token_response}
    except Exception as e:
        logger.exception(f"Token refresh failed for {crm_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/contacts")
def fetch_contacts(request: Request):
    logger.info("Fetching contacts from CRM")
    tokens = get_stored_tokens()
    if not tokens:
        logger.warning("No tokens found. Authentication required.")
        raise OAuthError(
            detail="Authorization required. Please authenticate with a CRM first.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    crm_name = tokens.get("crm_name")
    if not crm_name:
        logger.error("CRM name missing from stored tokens.")
        raise CRMIntegrationError(
            detail="Could not determine CRM from stored tokens.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not access_token or not refresh_token:
        logger.error("Missing access or refresh token in stored data.")
        raise TokenExchangeError(
            detail="Invalid token format. Missing required tokens.",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        page = int(request.query_params.get("page", 1))
        if page < 1:
            logger.error("Invalid page number provided.")
            raise InvalidPageNumberError(detail="Page number must be positive")
    except ValueError:
        logger.error("Page parameter is not a valid integer.")
        raise InvalidPageNumberError()

    try:
        plugin = get_plugin(crm_name.lower())
    except Exception as e:
        logger.exception(f"Plugin initialization failed for {crm_name}")
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
        logger.exception(f"Error fetching contacts from {crm_name}")
        raise ContactsFetchError(
            detail=f"Failed to fetch contacts from {crm_name}: {str(e)}",
            crm_name=crm_name,
            page=page
        )

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
    logger.info(f"Contacts saved to file: {filepath}")

    response_data["message"] = f"Contacts fetched from {crm_name} CRM and saved to {os.path.basename(filepath)}"
    return response_data
