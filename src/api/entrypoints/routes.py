from typing import Literal
from fastapi import APIRouter, Request
import requests
from addons.integration.plugins.capsule import get_contacts
from api.dependency import AnnotatedPluginManager, AnnotatedSettings

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
   

    url = "https://api.capsulecrm.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:8000/integration/callback", 
        "client_id": settings.auth.client_id,
        "client_secret": settings.auth.client_secret,

    }
    print(data)
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    response = requests.post(url, data=data, headers=headers)

    if response.status_code == 200:
        return {"access_token_response": response.json()}
    else:
        return {"error": response.text}
@router.get("/contacts")
def get_contacts_api(req: Request):
    access_token = req.headers.get("Authorization")  # Get the Bearer token from headers
    page_num = req.query_params.get('page')
    contacts = get_contacts(access_token,page=page_num)

    if "error" in contacts:
        return {"error": contacts["error"]}
    
    return {"contacts": contacts}





