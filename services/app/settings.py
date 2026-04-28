from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    kong_admin_token: str = Field(alias="AIAL_KONG_ADMIN_TOKEN")
    keycloak_client_secret: str = Field(alias="AIAL_KEYCLOAK_CLIENT_SECRET")
    oracle_username: str = Field(alias="AIAL_ORACLE_USERNAME")
    oracle_password: str = Field(alias="AIAL_ORACLE_PASSWORD")
    oracle_dsn: str = Field(alias="AIAL_ORACLE_DSN")
