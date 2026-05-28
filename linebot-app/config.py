import logging
import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import requests

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Application Settings configuration.
    Uses Pydantic Settings to load and validate variables from the environment
    and the .env file. If required variables are missing, it raises a
    ValidationError at startup, preventing runtime failures.
    """
    port: int = Field(default=8000, validation_alias="PORT")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    
    line_channel_id: str = Field(..., validation_alias="LINE_CHANNEL_ID")
    line_channel_secret: str = Field(..., validation_alias="LINE_CHANNEL_SECRET")
    line_channel_access_token: str = Field(..., validation_alias="LINE_CHANNEL_ACCESS_TOKEN")

    # Load from .env file if it exists, otherwise fall back to environment variables.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_line_channel_access_token(self) -> str | None:
        url = "https://api.line.me/v2/oauth/accessToken"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.line_channel_id,
            "client_secret": self.line_channel_secret
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            # 成功すると、JSONの中に 'access_token' が入って返ってきます
            return response.json().get("access_token")
        else:
            print(f"エラーが発生しました: {response.status_code}")
            print(response.text)
            return None

try:
    settings = Settings()
except Exception as e:
    logger.critical(
        f"Configuration validation failed. Check your .env file or environment variables. Error: {e}"
    )
    raise e
