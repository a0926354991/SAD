from fastapi import FastAPI, Request
from dotenv import load_dotenv
from line_bot_backend.db import add_user, get_all_ramen_shops  # render
from line_bot_backend.db import update_user_location, get_user_location, search_ramen_nearby
# from db import add_user, get_all_ramen_shops  # 本地
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import firestore # 毛加的 測試中

import os
import aiohttp
import random
import json
import math
from datetime import datetime, timezone, timedelta

load_dotenv()
app = FastAPI()
GeoPoint = firestore.GeoPoint

ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

RECOMMEND_KEYWORDS = ["推薦", "推薦拉麵", "拉麵推薦"]
UPLOAD_KEYWORDS = ["打卡","打卡上傳", "照片上傳"]
ANALYSIS_KEYWORDS = ["分析", "統整", "統整分析", "拉麵 dump", "拉麵 Dump", "拉麵dump", "拉麵Dump", "dump", "Dump"]
FEEDBACK_KEYWORDS = ["意見回饋", "回饋"]
FLAVORS = ["豚骨", "醬油", "味噌", "鹽味", "辣味", "雞白湯", "海老", "魚介"]

# 儲存使用者位置（之後要改用 Firestore，現在先這樣）
user_locations = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或改成你的前端網址
    allow_methods=["*"],
    allow_headers=["*"]
)

# 拿取所有拉麵店
@app.get("/all_shops")
def read_all_ramen_shops():
    shops = get_all_ramen_shops()
    return {"ramen_stores": shops}

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()
    print("📨 收到 LINE 傳來的內容：", json.dumps(body, indent=2, ensure_ascii=False))
    events = body.get("events", [])

    for event in events:
        event_type = event["type"]
        user_id = event["source"]["userId"]
        reply_token = event["replyToken"]

        # 取得使用者名稱
        profile = await get_user_profile(user_id)
        display_name = profile["displayName"] if profile else "Unknown"

        # 儲存使用者
        add_user(user_id, display_name)

        if event_type == "message":
            msg_type = event["message"]["type"]
            # print("📍 傳入訊息類型：", msg_type)

            # 1️⃣ 使用者傳文字訊息
            if msg_type == "text":
                msg = event["message"]["text"]

                # 打卡上傳
                if any(keyword in msg for keyword in UPLOAD_KEYWORDS):
                    await reply_message(reply_token, "【 打卡上傳 】\n功能實作中，敬請期待更多功能✨")
                
                # 統整分析
                elif any(keyword in msg for keyword in ANALYSIS_KEYWORDS):
                    await reply_message(reply_token, "【 統整分析 】\n功能實作中，敬請期待更多功能✨")
                
                # 意見回饋
                elif any(keyword in msg for keyword in FEEDBACK_KEYWORDS):
                    await reply_message(reply_token, "【 意見回饋 】\n功能實作中，敬請期待更多功能✨")
                
                # 拉麵推薦，處理判斷
                elif any(keyword in msg for keyword in RECOMMEND_KEYWORDS):
                    await reply_recommend(reply_token, user_id)

                # 使用者選擇口味
                elif msg.startswith("今天想吃的拉麵口味："):
                    flavor = msg.replace("今天想吃的拉麵口味：", "")
                    if flavor in FLAVORS:
                        is_valid, latlng = await is_location_valid(user_id)
                        if is_valid:
                            ramen_list = search_ramen_nearby(latlng.latitude, latlng.longitude, flavor)
                            await reply_ramen_carousel(reply_token, ramen_list)
                        else:
                            await reply_message(reply_token, "【 拉麵推薦 】\n請重新按左下角的加號➕，再次分享你的位置資訊📍")
                    else:
                        await reply_message(reply_token, "【 拉麵推薦 】\n請選擇正確的拉麵口味⚠️")


                # 隨機回覆拉麵文案
                else:
                    responses = [
                        "我目前的狀態：\n〇 曖昧\n〇 單身\n〇 穩定交往中\n● 拉 King 麵，我沒交往你，請別佔有我",
                        "「我喜歡你」這句話，太輕浮。\n「我愛你」這句話，太沈重。\n「要不要一起吃拉麵」這句話，剛剛好。",
                        "這是拿著拉麵的兔子，路過可以幫牠加叉燒\n (\_/)\n( ･ - ･) \n/>🍜>"
                    ]
                    reply_token = event["replyToken"]
                    random_reply = random.choice(responses)
                    await reply_message(reply_token, random_reply)

            # 2️⃣ 使用者傳位置
            elif msg_type == "location":
                latitude = event["message"]["latitude"]
                longitude = event["message"]["longitude"]
                # user_locations[user_id] = {"lat": latitude, "lng": longitude}
                update_user_location(user_id, latitude, longitude)
                await reply_ramen_flavor_flex_menu(reply_token)

    return {"status": "ok"}


#### Handle logic
async def is_location_valid(user_id: str, threshold_minutes: int = 5):
    latlng, last_updated = get_user_location(user_id)

    if last_updated is None:
        return False, None  # 沒有傳過位置

    now = datetime.now(timezone.utc)
    if now - last_updated < timedelta(minutes=threshold_minutes):
        return True, latlng
    else:
        return False, None

#### Reply message
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


## 回覆拉麵推薦
async def reply_recommend(reply_token, user_id):
    is_valid, _ = await is_location_valid(user_id)
    if is_valid:
        await reply_message(reply_token, "測試成功")
        await reply_ramen_flavor_flex_menu(reply_token)
    else:
        await reply_message(
            reply_token,
            "【 拉麵推薦 】\n請按左下角的加號➕，分享你的位置資訊，我會為你推薦附近的拉麵店！"
        )


## 選單訊息：拉麵口味選單（flex menu）
async def reply_ramen_flavor_flex_menu(reply_token):
    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "flex",
            "altText": "今天想吃哪種拉麵？請選擇拉麵口味！",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "今天想吃哪種拉麵？",
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": "選擇想吃的拉麵口味，我們為你推薦附近的拉麵店家",
                            "size": "sm",
                            "color": "#888888",
                            "wrap": True
                        },
                        *[
                            {
                                "type": "button",
                                "action": { "type": "message", "label": f"🍜 {flavor}", "text": f"今天想吃的拉麵口味：{flavor}"},
                                "style": "secondary",
                                "height": "sm",
                                "margin": "md",
                                "color": "#f0f0f0"
                            }
                            for flavor in FLAVORS
                        ]
                    ]
                },
                "styles": {
                    "body": { "backgroundColor": "#ffffff" }
                }
            }
        }]
    }

    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body, headers=headers) as resp:
            print("flex response status:", resp.status)
            print("response text:", await resp.text())


## 多頁訊息：回傳推薦拉麵店
async def reply_ramen_carousel(reply_token, ramen_list):
    columns = []
    for ramen in ramen_list[:10]:
        columns.append({
            "thumbnailImageUrl": ramen["image_url"],
            "title": ramen["name"][:40],
            "text": f"評價：{ramen['rating']}，距離：{ramen['distance']} 公尺",
            "actions": [
                # {"type": "uri", "label": "🗺️ 地圖導航", "uri": ramen["map_url"]},
                {"type": "message", "label": "📸 打卡上傳", "text": "打卡上傳"}
            ]
        })

    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "template",
            "altText": "拉麵推薦清單",
            "template": {
                "type": "carousel",
                "columns": columns
            }
        }]
    }
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=body, headers=headers)

# def haversine(lat1, lng1, lat2, lng2):
#     # Haversine formula
#     R = 6371
#     phi1 = math.radians(lat1)
#     phi2 = math.radians(lat2)
#     dphi = math.radians(lat2 - lat1)
#     dlambda = math.radians(lng2 - lng1)
#     a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
#     return 2 * R * math.asin(math.sqrt(a))

# async def search_ramen_nearby(lat, lng, flavor):
#     db = firestore.client()
#     # 取得所有有該 flavor 的拉麵店
#     docs = db.collection("ramen_shops").where("keywords", "array_contains", flavor).stream()
    
#     shops = []
#     async for doc in docs:
#         data = doc.to_dict()
#         shop_lat = data["location"]["latitude"]
#         shop_lng = data["location"]["longitude"]
#         dist = haversine(lat, lng, shop_lat, shop_lng)
#         shops.append({
#             "id": doc.id,
#             "name": data.get("name", ""),
#             "distance": dist,
#             "address": data.get("address", ""),
#             "image_url": data.get("menu_image", ""),
#             "rating": data.get("rating", 0),
#             "phone": data.get("phone", ""),
#             "lat": shop_lat,
#             "lng": shop_lng,
#             "keywords": data.get("keywords", []),
#             # 你可以加 rating, map_url, open_time, ...看你要回哪些
#         })
#     # 按照距離排序
#     shops.sort(key=lambda x: x["distance"])
#     return shops


# 假資料：搜尋附近的拉麵（你可以換成 Firebase 查詢）
# async def search_ramen_nearby(lat, lng, flavor):
#     return [
#         {
#             "name": f"{flavor}拉麵一號",
#             "rating": 4.8,
#             "distance": 120,
#             "image_url": "https://i.imgur.com/mkBdZbG.jpg",
#             "map_url": "https://maps.google.com",
#             "phone": "02-1234-5678"
#         },
#         {
#             "name": f"{flavor}拉麵二號",
#             "rating": 4.5,
#             "distance": 250,
#             "image_url": "https://i.imgur.com/kQyTd7H.jpg",
#             "map_url": "https://maps.google.com",
#             "phone": "02-2345-6789"
#         }
#     ]


async def get_user_profile(user_id: str):
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as res:
            if res.status == 200:
                return await res.json()
            else:
                return None


'''
## 選單訊息：拉麵口味選單
async def reply_ramen_flavor_quick_reply(reply_token):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "text",
            "text": "請選擇想吃的拉麵口味🍜",
            "quickReply": {
                "items": [
                    {"type": "action", "action": {"type": "message", "label": "豚骨", "text": "今天想吃的拉麵口味：豚骨"}},
                    {"type": "action", "action": {"type": "message", "label": "醬油", "text": "今天想吃的拉麵口味：醬油"}},
                    {"type": "action", "action": {"type": "message", "label": "味噌", "text": "今天想吃的拉麵口味：味噌"}},
                    {"type": "action", "action": {"type": "message", "label": "鹽味", "text": "今天想吃的拉麵口味：鹽味"}},
                    {"type": "action", "action": {"type": "message", "label": "辣味", "text": "今天想吃的拉麵口味：辣味"}},
                    {"type": "action", "action": {"type": "message", "label": "海鮮", "text": "今天想吃的拉麵口味：海鮮"}},
                    {"type": "action", "action": {"type": "message", "label": "雞白湯", "text": "今天想吃的拉麵口味：雞白湯"}},
                ]
            }
        }]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=body, headers=headers)
'''