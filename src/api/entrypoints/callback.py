# from fastapi import APIRouter, Depends, requests

# from config.settings import AuthSettings

# router = APIRouter(prefix="/integration", tags=["Integration"])


# @router.get("/callback")
# def generate_access_token(
#     code: str, 
#     state: str, 
#     settings: AuthSettings
# ):
   

#     url = "https://api.capsulecrm.com/oauth/token"
#     data = {
#         "grant_type": "authorization_code",
#         "code": code,
#         "redirect_uri": "http://localhost:8000/integration/callback", 
#         "client_id": settings.client_id,
#         "client_secret": settings.client_secret,
#     }
#     print(data)
#     headers = {'Content-Type': 'application/x-www-form-urlencoded'}

#     response = requests.post(url, data=data, headers=headers)

#     if response.status_code == 200:
#         return {"access_token_response": response.json()}
#     else:
#         return {"error": response.text}
