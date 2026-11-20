from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    erp_base_url: str = "http://192.168.145.64:8001"
    erp_api_key: str = ""
    gemini_api_key: str = ""
    jwt_secret_key: str = "change-me-in-production"
    admin_email: str = ""
    admin_password: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

