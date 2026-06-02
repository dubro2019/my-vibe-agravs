import base64
import hashlib
import hmac
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import httpx
from fastapi import FastAPI, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse

from config import settings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


# ==========================================
# Google Sheets API 設定
# ==========================================
SPREADSHEET_ID = "17IqhtAuv0bYGvci4KXT1rbH5V7ONn4xIZL3-gusRBz0" 
CREDENTIALS_FILE = "credentials.json"


def append_reservation_to_sheet(content: str, datetime_str: str) -> bool:
    """
    LINEボットで受け付けた予約情報をスプレッドシートの末尾に追加する関数
    """
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        
        # [内容, 日時] の順番で横一列に並べます
        values = [[content, datetime_str]]
        body = {"values": values}
        
        # 「シート1」のA列から始まる表の末尾にデータを追加
        range_name = "シート1!A:B"  
        
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        logger.info(f"スプレッドシートに書き込み成功: {result.get('updates').get('updatedCells')} セル更新")
        return True
    except Exception as e:
        logger.error(f"スプレッドシート書き込みエラー: {e}", exc_info=True)
        return False


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
                    
                    # 全角スペースを半角スペースに統一して、スペースで分割する
                    normalized_text = user_text.replace("　", " ")
                    split_text = normalized_text.split(maxsplit=1)  # 最初のスペースで2つに分ける
                    
                    # 正しいフォーマット（内容 と 日時 がスペースで区切られている）かチェック
                    if len(split_text) == 2:
                        reservation_content = split_text[0]  # 前半：内容
                        reservation_datetime = split_text[1] # 後半：日時
                        
                        # スプレッドシートへの書き込みを実行
                        success = append_reservation_to_sheet(
                            content=reservation_content, 
                            datetime_str=reservation_datetime
                        )
                        
                        if success:
                            reply_text = (
                                f"【予約を記録しました】\n"
                                f"メニュー: {reservation_content}\n"
                                f"希望日時: {reservation_datetime}\n"
                                f"スプレッドシートへ登録完了しました。"
                            )
                        else:
                            reply_text = "⚠️スプレッドシートへの書き込みに失敗しました。管理者にお問い合わせください。"
                    else:
                        # フォーマットが合っていない場合の案内メッセージ
                        reply_text = (
                            "⚠️予約のフォーマットが正しくありません。\n\n"
                            "「内容[スペース]日時」の形式で送信してください。\n"
                            "例：カット 06/10 14:00"
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
    