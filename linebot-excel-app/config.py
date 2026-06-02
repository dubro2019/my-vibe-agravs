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
    and the .env file.
    """
    port: int = Field(default=8000, validation_alias="PORT")
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    
    line_channel_id: str = Field(..., validation_alias="LINE_CHANNEL_ID")
    line_channel_secret: str = Field(..., validation_alias="LINE_CHANNEL_SECRET")
    line_channel_access_token: str = Field(..., validation_alias="LINE_CHANNEL_ACCESS_TOKEN")
    
    # ★ 変更: JSONパースエラーを避けるため、型を str でプレーンに受け取る
    line_target_user_ids_raw: str = Field(..., validation_alias="LINE_TARGET_USER_IDS")

    # ★ 追加: main.py から「.line_target_user_ids」としてアクセスされた時にリストを返すプロパティ
    @property
    def line_target_user_ids(self) -> list[str]:
        if not self.line_target_user_ids_raw:
            return []
        # カンマで分割し、前後の空白を除去、空文字を排除したリストを作成
        return [
            uid.strip() 
            for uid in self.line_target_user_ids_raw.split(",") 
            if uid.strip()
        ]

    # ==========================================
    # 【追加】リマインダー配信時刻の設定
    # ==========================================
    reminder_hour: int = Field(default=21, validation_alias="REMINDER_HOUR")
    reminder_minute: int = Field(default=0, validation_alias="REMINDER_MINUTE")
    reminder_timezone: str = Field(default="Asia/Tokyo", validation_alias="REMINDER_TIMEZONE")

    daily_reminder_text: str = Field(
        default="本日の日記を入力してください", 
        validation_alias="DAILY_REMINDER_TEXT"
    )

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