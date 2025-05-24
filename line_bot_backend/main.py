from fastapi import FastAPI, Request
from dotenv import load_dotenv
from line_bot_backend.db import add_user  # ✅ 改為使用 Firestore 函式
import os
import aiohttp

load_dotenv()
app = FastAPI()

ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()
    print("📨 收到 LINE 傳來的內容：", body)
    events = body.get("events", [])

    for event in events:
        if event["type"] == "message":
            user_id = event["source"]["userId"]
            msg = event["message"]["text"]

            # ✅ 新增使用者資料進 Firebase
            add_user(user_id, "Unknown")  # 初始 display_name 為 Unknown，可後續補上

            # 回傳訊息
            reply_token = event["replyToken"]
            await reply_message(reply_token, f"你說了：{msg}")

    return {"status": "ok"}

async def reply_message(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=body, headers=headers)
