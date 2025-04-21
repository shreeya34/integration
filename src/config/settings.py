from pydantic import BaseModel
from pydantic_settings import BaseSettings


class AuthSettings(BaseModel):
    client_id:str
    client_secret:str


class CrmSettings(BaseModel):
    code:str
    access_token:str


class AppSettings(BaseSettings):
    auth:AuthSettings
    crm:CrmSettings
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = '__'
