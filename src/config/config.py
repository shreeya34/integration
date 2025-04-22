from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CLIENT_ID: str
    CLIENT_SECRET: str
    REDIRECT_URI: str
    AUTH_URL: str
    TOKEN_URL: str

    class Config:
        env_file = ".env"


settings = Settings()

print(settings.CLIENT_ID)
print(settings.CLIENT_SECRET)
print(settings.REDIRECT_URI)
print(settings.AUTH_URL)
print(settings.TOKEN_URL)
