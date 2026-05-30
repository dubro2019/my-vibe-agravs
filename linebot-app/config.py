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
    line_target_user_id: str = Field(..., validation_alias="LINE_TARGET_USER_ID")

    # ==========================================
    # 【追加】リマインダー配信時刻の設定
    # ==========================================
    # .env に指定がない場合は、デフォルトで「21時00分（Asia/Tokyo）」になります。
    reminder_hour: int = Field(default=21, validation_alias="REMINDER_HOUR")
    reminder_minute: int = Field(default=0, validation_alias="REMINDER_MINUTE")
    reminder_timezone: str = Field(default="Asia/Tokyo", validation_alias="REMINDER_TIMEZONE")

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
        
        try:
            response = requests.post(url, headers=headers, data=data)
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                # print から logger.error へ変更し、本番ログに統合
                logger.error(f"LINEアクセストークンの取得に失敗しました。ステータスコード: {response.status_code}, レスポンス: {response.text}")
                return None
        except Exception as e:
            logger.error(f"LINEアクセストークン取得中に予期せぬエラーが発生しました: {e}", exc_info=True)
            return None

try:
    settings = Settings()
except Exception as e:
    logger.critical(
        f"Configuration validation failed. Check your .env file or environment variables. Error: {e}"
    )
    raise e
