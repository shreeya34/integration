from pydantic import BaseModel, Field
from typing import Dict, Any, List

from pydantic_settings import BaseSettings


class CRMOAuthConfig(BaseModel):
    auth_url: str
    token_url: str
    scope: str
    redirect_path: str


class CRMSettings(BaseModel):
    client_id: str
    client_secret: str
    config: CRMOAuthConfig


class AppSettings(BaseSettings):
    crms: Dict[str, CRMSettings] = Field(..., alias="CRMS")
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
