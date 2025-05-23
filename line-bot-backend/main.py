from fastapi import FastAPI, Request
from db import init_db, SessionLocal, User
from dotenv import load_dotenv
import os
import aiohttp

load_dotenv()
app = FastAPI()
init_db()

ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()
    # print("📨 收到 LINE 傳來的內容：", body)   # ✅ 建議加這行
    events = body.get("events", [])

    for event in events:
        if event["type"] == "message":
            # print("📌 event = ", event)  # 印出每個事件完整內容
            user_id = event["source"]["userId"]
            msg = event["message"]["text"]

            db = SessionLocal()
            user = db.query(User).filter_by(line_user_id=user_id).first()
            if not user:
                user = User(line_user_id=user_id, display_name="Unknown")
                db.add(user)
                db.commit()

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
