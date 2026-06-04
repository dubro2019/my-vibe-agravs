import base64
from email import message
import hashlib
import hmac
import logging
from contextlib import asynccontextmanager
# from turtle import title
from typing import Dict, Any

import httpx
from fastapi import FastAPI, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse

from config import settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ==========================================
# 1. 認証設定とカレンダー認証用クライアントの作成
# ==========================================
# ダウンロードしたサービスアカウントのJSONファイルのパス
KEY_FILE_LOCATION = "/home/yutaka/src/linebot-calendar-app/credentials_calendar.json"
# 控えておいたカレンダーID
CALENDAR_ID = "yuta.hasegawa@gmail.com"

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE_LOCATION, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=creds)


# ==========================================
# 1. Logging Setup (Production Grade)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("line-bot")


# ==========================================
# 2. FastAPI Lifespan Manager (Connection Pool)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle.
    Initializes a global httpx.AsyncClient during startup and closes it on shutdown.
    Also starts the APScheduler for daily reminder at configured JST time.
    """
    logger.info("Initializing HTTP client connection pool...")
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    app.state.http_client = httpx.AsyncClient(
        limits=limits,
        timeout=httpx.Timeout(10.0, connect=2.0)
    )
    # -------------------- Scheduler start --------------------
    scheduler = AsyncIOScheduler()
    
    reminder_hour = getattr(settings, "reminder_hour", 21)
    reminder_minute = getattr(settings, "reminder_minute", 0)
    reminder_timezone = getattr(settings, "reminder_timezone", "Asia/Tokyo")

    trigger = CronTrigger(hour=reminder_hour, minute=reminder_minute, timezone=reminder_timezone)
    scheduler.add_job(daily_reminder_job, trigger)
    scheduler.start()
    
    logger.info(f"APScheduler started – daily reminder scheduled at {reminder_hour:02d}:{reminder_minute:02d} ({reminder_timezone}).")
    app.state.scheduler = scheduler
    # -------------------------------------------------------
    yield
    # -------------------- Scheduler shutdown --------------------
    logger.info("Shutting down scheduler and HTTP client...")
    scheduler.shutdown(wait=False)
    await app.state.http_client.aclose()


# Initialize FastAPI with lifespan management
app = FastAPI(
    title="LINE Resilient Echo Bot Backend",
    description="A robust, production-ready LINE webhook echo bot.",
    version="1.0.0",
    lifespan=lifespan
)


# ==========================================
# 3. Signature Verification Helper
# ==========================================
def verify_line_signature(body: bytes, signature: str, secret: str) -> bool:
    """
    Verifies that the request payload actually originated from the LINE server.
    """
    if not signature:
        logger.error("Missing X-Line-Signature header.")
        return False

    try:
        hash_obj = hmac.new(
            key=secret.encode("utf-8"),
            msg=body,
            digestmod=hashlib.sha256
        )
        calculated_signature = base64.b64encode(hash_obj.digest()).decode("utf-8")
        
        is_valid = hmac.compare_digest(calculated_signature, signature)
        if not is_valid:
            logger.warning(
                f"Signature mismatch. Calculated: {calculated_signature} vs Header: {signature}"
            )
        return is_valid
    except Exception as e:
        logger.error(f"Error during signature verification: {e}", exc_info=True)
        return False


# ==========================================
# 4. Outbound LINE API Client Helper
# ==========================================
async def send_line_reply(
    http_client: httpx.AsyncClient,
    reply_token: str,
    text: str
) -> None:
    """
    Sends the echo back response to the LINE Messaging API.
    """
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer { settings.get_line_channel_access_token() }"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }

    try:
        logger.info(f"Sending reply message for token {reply_token[:8]}...")
        response = await http_client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Successfully sent reply to LINE. Status Code: {response.status_code}")
    except httpx.HTTPStatusError as e:
        logger.error(
            f"LINE API responded with error status: {e.response.status_code}. Response: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error occurred while calling LINE API: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while sending reply: {e}", exc_info=True)


# ------------------------------------------------------------
# Push Message Helper (uses shared httpx client)
# ------------------------------------------------------------
async def push_line_message(http_client: httpx.AsyncClient, user_id: str, text: str) -> None:
    """Send a push message to a specified LINE user."""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer { settings.get_line_channel_access_token() }"
    }
    payload = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    try:
        response = await http_client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Push message sent to {user_id[:8]} – status {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to push message to {user_id}: {e}")
        raise


# ------------------------------------------------------------
# Scheduled job – daily reminder
# ------------------------------------------------------------
async def daily_reminder_job() -> None:
    """Send daily reminder to multiple users."""
    http_client: httpx.AsyncClient = app.state.http_client
    user_ids = getattr(settings, "line_target_user_ids", [])  
    reminder_text = getattr(settings, "daily_reminder_text", "本日の日記を入力してください")
    
    for user_id in user_ids:
        if not user_id.strip():
            continue
            
        try:
            await push_line_message(http_client, user_id.strip(), reminder_text)
        except Exception as exc:
            error_text = f"⚠️ リマインダー送信に失敗しました: {exc}"
            try:
                await push_line_message(http_client, user_id.strip(), error_text)
            except Exception:
                logger.error(f"Failed to send error notification to user: {user_id}")


# ==========================================
# 2. カレンダー登録用のメイン関数
# ==========================================
def register_to_calendar(title, datetime_clean_str):
    """
    datetime_clean_str は "2026/03/05 12:00" のような形式を想定
    """
    service = get_calendar_service()

    try:

        # 表記ゆれを許容してパースするための変換処理
        # もしスラッシュではなくハイフンだった場合はスラッシュに統一
        normalized_dt = datetime_clean_str.replace("-", "/")
        
        # %Y/%m/%d は一桁（3/5）でも二桁（03/05）でも柔軟に解釈してくれます
        start_time = datetime.strptime(normalized_dt, "%Y/%m/%d %H:%M")
        end_time = start_time + timedelta(hours=1)
    except ValueError as val_err:
        logger.error(f"日時のフォーマット解析に失敗しました ({datetime_clean_str}): {val_err}")
        return False

    event = {
        "summary": title,
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "Asia/Tokyo",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "Asia/Tokyo",
        },
    }

    try:
        event_result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logger.info(f"予定を登録しました: {event_result.get('htmlLink')}")
        return True
    except Exception as e:
        logger.error(f"カレンダー登録エラー: {e}", exc_info=True)
        return False

# ==========================================
# 5. Core Webhook Handler (/callback)
# ==========================================
@app.post("/callback", summary="LINE Webhook Callback Endpoint")
async def callback(
    request: Request,
    x_line_signature: str = Header(None, alias="X-Line-Signature")
):
    """
    Receives events from the LINE Platform.
    """
    # 1. Read Raw Request Body
    raw_body = await request.body()
    
    # 2. Perform Security Verification
    if not verify_line_signature(raw_body, x_line_signature, settings.line_channel_secret):
        logger.warning("Unauthorized access attempt. Invalid LINE signature.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # 3. Parse JSON Body
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON body: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    events = payload.get("events", [])
    logger.info(f"Received webhook callback containing {len(events)} event(s).")

    # Get the shared HTTP client from application state
    http_client = request.app.state.http_client

    # 4. Handle Each Event Asynchronously & Resiliently
    for event in events:
        try:
            event_type = event.get("type")
            reply_token = event.get("replyToken")
            
            if not reply_token:
                logger.info(f"Skipping event type '{event_type}' which lacks a replyToken.")
                continue

            # Handle message events
            if event_type == "message":
                message = event.get("message", {})
                message_type = message.get("type")

                # We only process text messages
                if message_type == "text":

                    user_text = message.get("text").strip()
                    logger.info(f"Received text message event. Content: '{user_text}'")
                    
                    # 💡【修正】ここで一気に全角英数字・全角スペースをすべて半角に正規化します
                    import unicodedata
                    normalized_text = unicodedata.normalize("NFKC", user_text)
                    
                    import re
                    # 2. 正規表現で「末尾の日時（年/月/日 時:分 または 年-月-日 時:分）」を検索
                    # パターン解説:
                    #   (\d{4}[-/]\d{1,2}[-/]\d{1,2}) -> グループ1: 年(4桁)[-/]月(1~2桁)[-/]日(1~2桁)
                    #   \s+                           -> 1文字以上の空白
                    #   (\d{1,2}:\d{2})               -> グループ2: 時(1~2桁):分(2桁)
                    match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+(\d{1,2}:\d{2})$", normalized_text)
                    
                    if match:
                        # マッチした位置より前をタイトル（項目）とする
                        reservation_content = normalized_text[:match.start()].strip()
                        
                        # 日付と時刻を綺麗に結合（例: "2026/3/5 12:00"）
                        date_part = match.group(1)
                        time_part = match.group(2)
                        reservation_datetime = f"{date_part} {time_part}"
                        
                        # タイトルが空っぽ（日時しか入力されてない）場合のガード
                        if not reservation_content:
                            reservation_content = "予定"

                        # カレンダー登録関数を呼び出す
                        success = register_to_calendar(reservation_content, reservation_datetime)
                                                
                        if success:
                            reply_text = (
                                f"【予定を登録しました】\n"
                                f"タイトル: {reservation_content}\n"
                                f"登録日時: {reservation_datetime}\n"
                                f"Google Calendarへ登録完了しました。"
                            )
                        else:
                            # 既存コードの文言（※カレンダーに合わせた内容に微修正）
                            reply_text = "⚠️Googleカレンダーへの書き込みに失敗しました。時間設定やシステムエラーの可能性があります。"
                    else:
                        # フォーマットが合っていない場合の案内メッセージ
                        reply_text = (
                            "⚠️予定のフォーマットが正しくありません。\n\n"
                            "「タイトル [スペース] 日時」の形式で送信してください。\n"
                            "例：会食 2026/06/10 14:00\n"
                            "※タイトルにスペースが含まれていても大丈夫です！"
                        )
                    
                    # ユーザーに入力結果（またはエラー案内）を返信する
                    await send_line_reply(http_client, reply_token, reply_text)


        except Exception as event_err:
            logger.error(
                f"Error occurred while processing event {event.get('id', 'unknown')}: {event_err}",
                exc_info=True
            )
            continue

    return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)


# ==========================================
# 6. Basic Health Check Endpoint
# ==========================================
@app.get("/health", summary="Health Check")
async def health_check():
    return {"status": "healthy", "service": "line-bot-backend"}


# ------------------------------------------------------------
# Test endpoint to manually trigger a push (development only)
# ------------------------------------------------------------
@app.get("/test-push", summary="Manual push test")
async def test_push():
    http_client = app.state.http_client
    user_ids = getattr(settings, "line_target_user_ids", [])
    
    sent_count = 0
    for user_id in user_ids:
        if not user_id.strip():
            continue
        await push_line_message(http_client, user_id.strip(), "テストプッシュメッセージ")
        sent_count += 1
        
    return {"status": "push_sent", "targets_count": sent_count}


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {settings.host}:{settings.port}...")
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
    