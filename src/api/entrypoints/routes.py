from typing import Literal
from fastapi import APIRouter, Request
import requests
from addons.integration.plugins.capsule import get_contacts
from addons.storage import save_contacts_to_json
from api.dependency import AnnotatedPluginManager, AnnotatedSettings
from addons.integration.plugins.capsule import exchange_token

from config.settings import AuthSettings


router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("/authorization-url")
def get_authorization_url_resource(
    pm: AnnotatedPluginManager,
    settings: AnnotatedSettings,
    name: Literal["copper", "capsule"] | None = None,
): 
    return pm.hook.get_auth_url(settings=settings.auth)


   


@router.get("/callback")
def generate_access_token(
    code: str, 
    state: str, 
    settings: AnnotatedSettings,
):
    print(f"CODE: {code}")
    print(f"STATE: {state}")
    
    token_response = exchange_token(
        code=code,
        client_id=settings.auth.client_id,
        client_secret=settings.auth.client_secret,
    )

    if token_response:
        return {"access_token_response": token_response}
    else:
        return {"error": "Failed to fetch access token"}


    
@router.get("/contacts")
def get_contacts_api(req: Request):
    access_token = req.headers.get("Authorization")  
    page_num = req.query_params.get('page')
    contacts = get_contacts(access_token,page=page_num)

    if "error" in contacts:
        return {"error": contacts["error"]}
    
    save_contacts_to_json(contacts)
    return {"contacts": contacts}





