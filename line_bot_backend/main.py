from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from dotenv import load_dotenv
from line_bot_backend.db import add_user, get_all_ramen_shops, get_user_by_id, update_user_location, get_user_location, search_ramen_nearby, create_checkin, upload_photo
# from db import add_user, get_all_ramen_shops  # 本地
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import firestore, storage # 新增：storage
from pydantic import BaseModel

import os
import aiohttp
import random
import json
import math
from datetime import datetime, timezone, timedelta
import uuid  # 新增：用於生成唯一檔名

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

# 拿取拉麵店
@app.get("/all_shops")
def read_all_ramen_shops():
    shops = get_all_ramen_shops()
    return {"ramen_stores": shops}

# 新增：檢查使用者登入狀態
@app.get("/users/{user_id}")
def check_user(user_id: str):
    user = get_user_by_id(user_id)
    print(f"🔍 Retrieved user: {user}")
    if user:
        return {"status": "success", "user": user}
    raise HTTPException(status_code=404, detail="User not found")

class CheckInRequest(BaseModel):
    store_id: str
    user_id: str
    rating: float
    comment: str = ""
    photo_url: str = ""  # 新增：照片 URL

@app.post("/checkin")
def checkin(data: CheckInRequest):
    # ✅ 呼叫你的 Firestore 函數
    success, message = create_checkin(data.dict())
    if success:
        return {"status": "success", "message": message}
    raise HTTPException(status_code=400, detail=message)

# 新增：照片上傳 endpoint
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 檢查檔案類型
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="只能上傳圖片檔案")
        
        # 讀取檔案內容
        content = await file.read()
        
        # 使用 db.py 中的函數上傳照片
        success, result = upload_photo(content, file.content_type)
        
        if success:
            return {
                "status": "success",
                "url": result
            }
        else:
            raise HTTPException(status_code=500, detail=result)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
                            await reply_ramen_flex_carousel(reply_token, ramen_list)

                            # 取出 ramen_list 的 id 組合網址
                            shop_ids = [ramen["id"] for ramen in ramen_list[:10]]  # 只取 carousel 有顯示的
                            ids_str = ",".join(shop_ids)
                            roulette_url = f"https://frontend-7ivv.onrender.com/ramen-map/?show_wheel=1&store_ids={ids_str}"

                            # 傳一個訊息給使用者
                            reply_text = f"🎲 沒辦法決定要吃哪一家嗎？點這裡進入轉盤\n{roulette_url}"
                            await push_message(user_id, reply_text)
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
                update_user_location(user_id, latitude, longitude)
                await reply_ramen_flavor_flex_menu(reply_token)

    return {"status": "ok"}

async def push_message(user_id, text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": user_id,
        "messages": [{
            "type": "text",
            "text": text
        }]
    }
    async with aiohttp.ClientSession() as session:
        await session.post(url, json=body, headers=headers)


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
                    "borderWidth": "2px",
                    "borderColor": "#FFE175",  # 你可以調整顏色
                    # "cornerRadius": "10px",    # 加一點圓角更好看（可選）
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
                            "text": "請選擇想吃的拉麵口味，我們為你推薦附近的拉麵店家🍜",
                            "size": "sm",
                            "color": "#888888",
                            "wrap": True
                        },
                        *[
                            {
                                "type": "button",
                                "action": { "type": "message", "label": f"{flavor}", "text": f"今天想吃的拉麵口味：{flavor}"},
                                "style": "secondary",
                                "height": "sm",
                                "margin": "md",
                                "color": "#FDEDC7"
                            }
                            for flavor in FLAVORS
                        ]
                    ]
                },
                "styles": {
                    "body": { "backgroundColor": "#FCF9F4" }
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

async def reply_ramen_new_flex_carousel(reply_token, ramen_list):
    bubbles = []

    for ramen in ramen_list[:10]:
        dist = ramen['distance']
        dist_str = f"{int(dist * 1000)} 公尺" if dist < 1 else f"{dist:.2f} 公里"
        rating_text = f"{ramen['rating']} ⭐️" if ramen['rating'] is not None else "尚未有評分"

        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "lg",  # 外層 padding，形成邊框感
                "backgroundColor": "#A9C4EB",  # 外層底色（邊框視覺）
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "paddingAll": "md",
                        "backgroundColor": "#FCF9F4",  # 內層卡片
                        "cornerRadius": "md",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "image",
                                "url": ramen["image_url"],
                                "size": "full",
                                "aspectRatio": "20:13",
                                "aspectMode": "cover"
                            },
                            {
                                "type": "text",
                                "text": ramen["name"][:40],
                                "wrap": True,
                                "weight": "bold",
                                "size": "lg",
                                "color": "#063D74"
                            },
                            {
                                "type": "text",
                                "text": f"評價：{rating_text}\n距離：{dist_str}",
                                "wrap": True,
                                "size": "sm"
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "md",
                                "margin": "md",
                                "contents": [
                                    {
                                        "type": "button",
                                        "style": "secondary",
                                        "color": "#D5E3F7",
                                        "action": {
                                            "type": "uri",
                                            "label": "🗺️ 地圖查看",
                                            "uri": f"https://frontend-7ivv.onrender.com/ramen-map/?store_id={ramen['id']}"
                                        }
                                    },
                                    {
                                        "type": "button",
                                        "style": "secondary",
                                        "color": "#D5E3F7",
                                        "action": {
                                            "type": "message",
                                            "label": "📸 打卡上傳",
                                            "text": "打卡上傳"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        bubbles.append(bubble)

    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "flex",
            "altText": "拉麵推薦清單",
            "contents": {
                "type": "carousel",
                "contents": bubbles
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


## 多頁訊息：回傳推薦拉麵店 (flex message)
async def reply_ramen_flex_carousel(reply_token, ramen_list):
    bubbles = []

    for ramen in ramen_list[:10]:
        dist = ramen['distance']
        if dist < 1:
            dist_str = f"{int(dist * 1000)} 公尺"
        else:
            dist_str = f"{dist:.2f} 公里"
        rating_text = f"{ramen['rating']} ⭐️" if ramen['rating'] is not None else "尚未有評分"

        bubble = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": ramen["image_url"],
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "text",
                        "text": ramen["name"][:40],
                        "wrap": True,
                        "weight": "bold",
                        "size": "lg",
                        "color": "#063D74"
                    },
                    {
                        "type": "text",
                        "text": f"評價：{rating_text}\n距離：{dist_str}",
                        "wrap": True,
                        "size": "sm",
                        # "color": "#888888"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "color": "#D5E3F7",
                        "action": {
                            "type": "uri",
                            "label": "🗺️ 地圖查看",
                            "uri": f"https://frontend-7ivv.onrender.com/ramen-map/?store_id={ramen['id']}"
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "color": "#D5E3F7",
                        "action": {
                            "type": "message",
                            "label": "📸 打卡上傳",
                            "text": "打卡上傳"
                        }
                    }
                ]
            },
            "styles": {
                "body": {"backgroundColor": "#FFFFFF"},
                "footer": {"backgroundColor": "#FFFFFF"}
            }
        }
        bubbles.append(bubble)

    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "flex",
            "altText": "拉麵推薦清單",
            "contents": {
                "type": "carousel",
                "contents": bubbles
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


## 多頁訊息：回傳推薦拉麵店
# async def reply_ramen_carousel(reply_token, ramen_list):
#     columns = []
#     for ramen in ramen_list[:10]:
#         dist = ramen['distance']
#         if dist < 1:
#             dist_str = f"{int(dist * 1000)} 公尺"
#         else:
#             dist_str = f"{dist:.2f} 公里"
#         rating_text = f"{ramen['rating']} ⭐️" if ramen['rating'] is not None else "尚未有評分"
#         columns.append({
#             "thumbnailImageUrl": ramen["image_url"],
#             "title": ramen["name"][:40],
#             "text": f"評價：{rating_text}\n距離：{dist_str}",
#             "actions": [
#                 {
#                     "type": "uri",
#                     "label": "🗺️ 地圖查看",
#                     "uri": f"https://frontend-7ivv.onrender.com/ramen-map/?store_id={ramen['id']}"
#                 },
#                 {"type": "message", "label": "📸 打卡上傳", "text": "打卡上傳"}
#             ]
#         })

#     body = {
#         "replyToken": reply_token,
#         "messages": [{
#             "type": "template",
#             "altText": "拉麵推薦清單",
#             "template": {
#                 "type": "carousel",
#                 "columns": columns
#             }
#         }]
#     }
#     url = "https://api.line.me/v2/bot/message/reply"
#     headers = {
#         "Authorization": f"Bearer {ACCESS_TOKEN}",
#         "Content-Type": "application/json"
#     }
#     async with aiohttp.ClientSession() as session:
#         await session.post(url, json=body, headers=headers)

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



