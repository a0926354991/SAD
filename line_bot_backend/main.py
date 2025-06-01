from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from dotenv import load_dotenv
from line_bot_backend.db import db, add_user, get_all_ramen_shops, get_user_by_id, update_user_location, get_user_location, search_ramen_nearby, create_checkin, upload_photo, get_store_checkins, get_user_checkins
# from db import add_user, get_all_ramen_shops  # 本地
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import firestore, storage # 新增：storage
from pydantic import BaseModel
from urllib.parse import quote
from collections import Counter
from PIL import Image, ImageOps

import io
import os
import aiohttp
import random
import json
import math
import requests
import urllib.parse
from datetime import datetime, timezone, timedelta
import uuid  # 新增：用於生成唯一檔名
import matplotlib
import matplotlib.pyplot as plt
import asyncio
from io import BytesIO

load_dotenv()
app = FastAPI()
GeoPoint = firestore.GeoPoint
db = firestore.client()

ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

RECOMMEND_KEYWORDS = ["推薦", "推薦拉麵", "拉麵推薦"]
ANALYSIS_KEYWORDS = ["統整", "統整分析"]
FLAVORS = ["豚骨", "醬油", "味噌", "鹽味", "辣味", "雞白湯", "海老", "魚介"]
# FEEDBACK_KEYWORDS = ["意見回饋", "回饋"]
# UPLOAD_KEYWORDS = ["打卡","打卡上傳", "照片上傳"]
# DUMP_KEYWORDS = ["生成我的拉麵 dump", "拉麵 dump", "拉麵 Dump", "拉麵dump", "拉麵Dump", "dump", "Dump"]

# 儲存使用者位置（之後要改用 Firestore，現在先這樣）
user_locations = {}
user_last_days: dict[str,int] = {}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

#### 拿取拉麵店
@app.get("/all_shops")
def read_all_ramen_shops():
    shops = get_all_ramen_shops()
    return {"ramen_stores": shops}

@app.get("/nearby_shops")
def get_nearby_shops(lat: float, lng: float, limit: int = 6):
    try:
        # 驗證輸入參數
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            raise HTTPException(status_code=400, detail="Invalid latitude or longitude")
        
        if not isinstance(limit, int) or limit <= 0:
            raise HTTPException(status_code=400, detail="Invalid limit value")
            
        # 驗證經緯度範圍
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise HTTPException(status_code=400, detail="Latitude or longitude out of range")
            
        # 使用 search_ramen_nearby 函數，不指定口味，獲取所有附近的店
        shops = search_ramen_nearby(lat, lng, None)
        # 限制返回數量
        shops = shops[:limit]
        
        return {"status": "success", "shops": shops}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in get_nearby_shops: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")



#### 新增：檢查使用者登入狀態
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
    keyword: str
    comment: str = ""
    photo_url: str = ""  # 新增：照片 URL

@app.post("/checkin")
def checkin(data: CheckInRequest):
    # ✅ 呼叫你的 Firestore 函數
    success, message = create_checkin(data.dict())
    if success:
        return {"status": "success", "message": message}
    raise HTTPException(status_code=400, detail=message)



#### 新增：照片上傳 endpoint
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

@app.get("/store_checkins/{store_id}")
def get_store_checkins_api(store_id: str, limit: int = 5, last_id: str = None):
    try:
        checkins, has_more = get_store_checkins(store_id, limit, last_id)
        return {
            "status": "success",
            "checkins": checkins,
            "has_more": has_more
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user_checkins/{user_id}")
def get_user_checkins_api(user_id: str, limit: int = 5, last_id: str = None):
    try:
        checkins, has_more = get_user_checkins(user_id, limit, last_id)
        return {
            "status": "success",
            "checkins": checkins,
            "has_more": has_more
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



#### Main
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
                
                # 統整分析
                if any(keyword in msg for keyword in ANALYSIS_KEYWORDS):
                    await reply_analysis_flex_menu(reply_token)

                elif msg in ["分析最近 7 天的結果", "分析最近 30 天的結果", "分析最近 90 天的結果"]:
                    msg = msg.replace("分析最近 ", "")
                    msg = msg.replace(" 天的結果", "")
                    days = int(msg)
                    await handle_analysis(reply_token, user_id, days)

                elif msg == "生成 4 格 dump":
                    await reply_message(reply_token, "稍等一下，你的拉麵 dump 正在生成中⋯⋯")
                    asyncio.create_task(handle_ramen_dump(reply_token, user_id, max_tiles=4))
                elif msg == "生成 6 格 dump":
                    await reply_message(reply_token, "稍等一下，你的拉麵 dump 正在生成中⋯⋯")
                    asyncio.create_task(handle_ramen_dump(reply_token, user_id, max_tiles=6))
                elif msg == "生成 12 格 dump":
                    await reply_message(reply_token, "稍等一下，你的拉麵 dump 正在生成中⋯⋯")
                    asyncio.create_task(handle_ramen_dump(reply_token, user_id, max_tiles=12))
                
                # 拉麵推薦，處理判斷
                elif any(keyword in msg for keyword in RECOMMEND_KEYWORDS):
                    await reply_recommend(reply_token, user_id)

                # 使用者選擇口味
                elif msg.startswith("今天想吃的拉麵口味："):
                    flavor = msg.replace("今天想吃的拉麵口味：", "")
                    is_valid, latlng = await is_location_valid(user_id)
                    if is_valid:
                        if flavor in FLAVORS:
                            ramen_list = search_ramen_nearby(latlng.latitude, latlng.longitude, flavor)
                            await reply_ramen_flex_carousel(reply_token, ramen_list)

                            # 取出 ramen_list 的 id 組合網址
                            shop_ids = [ramen["id"] for ramen in ramen_list[:10]]  # 只取 carousel 有顯示的
                            # ids_str = ",".join(shop_ids)
                            encoded_store_ids = quote(",".join(shop_ids))
                            roulette_url = f"https://liff.line.me/2007489792-4popYn8a#show_wheel=1&store_ids={encoded_store_ids}"

                            # 傳一個訊息給使用者
                            await push_ramen_wheel(user_id, roulette_url)
                            # reply_text = f"🎲 沒辦法決定要吃哪一家嗎？點這裡進入轉盤\n{roulette_url}"
                            # await push_template(user_id, message)

                        elif flavor == "全部":
                            ramen_list = search_ramen_nearby(latlng.latitude, latlng.longitude)
                            await reply_ramen_flex_carousel(reply_token, ramen_list)

                            # 取出 ramen_list 的 id 組合網址
                            shop_ids = [ramen["id"] for ramen in ramen_list[:10]]  # 只取 carousel 有顯示的
                            # ids_str = ",".join(shop_ids)
                            encoded_store_ids = quote(",".join(shop_ids))
                            roulette_url = f"https://liff.line.me/2007489792-4popYn8a#show_wheel=1&store_ids={encoded_store_ids}"

                            # 傳一個訊息給使用者
                            await push_ramen_wheel(user_id, roulette_url)
                            # reply_text = f"🎲 沒辦法決定要吃哪一家嗎？點這裡進入轉盤\n{roulette_url}"
                            # await push_message(user_id, reply_text)

                        else:
                            await reply_message(reply_token, "【 拉麵推薦 】\n請選擇正確的拉麵口味⚠️")
                    else:
                        await reply_message(reply_token, "【 拉麵推薦 】\n請重新按左下角的加號➕，再次分享你的位置資訊📍")


                # 隨機回覆拉麵文案
                else:
                    responses = [
                        "我目前的狀態：\n〇 曖昧\n〇 單身\n〇 穩定交往中\n● 拉 King 麵，我沒交往你，請別佔有我",
                        "「我喜歡你」這句話，太輕浮。\n「我愛你」這句話，太沈重。\n「加麵免費」這句話，剛剛好。",
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

            else:
                responses = [
                    "我目前的狀態：\n〇 曖昧\n〇 單身\n〇 穩定交往中\n● 拉 King 麵，我沒交往你，請別佔有我",
                    "「我喜歡你」這句話，太輕浮。\n「我愛你」這句話，太沈重。\n「要不要一起吃拉麵」這句話，剛剛好。",
                    "這是拿著拉麵的兔子，路過可以幫牠加叉燒\n (\_/)\n( ･ - ･) \n/>🍜>"
                ]
                reply_token = event["replyToken"]
                random_reply = random.choice(responses)
                await reply_message(reply_token, random_reply)

    return {"status": "ok"}



#### Handle logic
async def is_location_valid(user_id: str, threshold_minutes: int = 3):
    latlng, last_updated = get_user_location(user_id)

    if last_updated is None:
        return False, None  # 沒有傳過位置
    if latlng == GeoPoint(0, 0):
        return False, None  # 沒有傳過位置

    now = datetime.now(timezone.utc)
    if now - last_updated < timedelta(minutes=threshold_minutes):
        return True, latlng
    else:
        return False, None
    
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



#### Reply or push
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

async def push_message(user_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": user_id,
        "messages": [message] if isinstance(message, dict) else [{"type": "text", "text": message}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body, headers=headers) as resp:
            print("Status:", resp.status)
            print("Body:", json.dumps(body, indent=2))
            print("Response:", await resp.text())

async def push_template(user_id, message):                ## 這個應該沒有用到
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": user_id,
        "messages": [message]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body, headers=headers) as resp:
            print("Status:", resp.status)
            print("Body:", json.dumps(body, indent=2))
            print("Response:", await resp.text())

async def reply_image(reply_token: str, image_url: str):  ## 這個應該沒有用到
    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        }]
    }
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        await session.post("https://api.line.me/v2/bot/message/reply", json=body, headers=headers)



## 拉麵推薦
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
                    "borderWidth": "4px",
                    "borderColor": "#FFE175",  # 你可以調整顏色
                    "cornerRadius": "18px",    # 加一點圓角更好看（可選）
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
                        # {"type": "spacer", "size": "md"},
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "height": "10px" # 控制空白區塊高度
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
                        ],
                        {
                            "type": "button",
                            "action": { "type": "message", "label": "我要全部！", "text": "今天想吃的拉麵口味：全部"},
                            "style": "secondary",
                            "height": "sm",
                            "margin": "md",
                            "color": "#FDEDC7"
                        }
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
                        "size": "sm"
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "color": "#D5E3F7",
                        "action": {
                            "type": "uri",
                            "label": "🗺️ 地圖查看",
                            "uri": f"https://liff.line.me/2007489792-4popYn8a#store_id={ramen['id']}"
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "color": "#D5E3F7",
                        "action": {
                            "type": "uri",
                            "label": "📸 打卡上傳",
                            "uri": f"https://liff.line.me/2007489792-4popYn8a#store_id={ramen['id']}&checkin=1"
                        }
                    }
                ]
            },
            "styles": {
                "body": {"backgroundColor": "#FCF9F4"},
                # "footer": {"backgroundColor": "#FFFFFF"}
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

## 拉麵轉盤按鈕 (flex message)
async def push_ramen_wheel(user_id, roulette_url):
    message = {
        "type": "flex",
        "altText": "點擊進入拉麵轉盤！",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "borderWidth": "4px",
                "borderColor": "#A9C4EB",
                "cornerRadius": "18px",
                "contents": [
                    {
                        "type": "text",
                        "text": "沒辦法決定要吃哪一家嗎？",
                        "weight": "bold",
                        "size": "lg",
                        "wrap": True
                    },
                    # {"type": "spacer", "size": "md"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "height": "10px" # 控制空白區塊高度
                    },
                    {
                        "type": "button",
                        "action":{ "type": "uri", "label": "🎲 進入拉麵轉盤", "uri": roulette_url},
                        "style": "secondary",
                        "height": "md",
                        "margin": "md",
                        "color": "#D5E3F7"
                    },
                ]
            },
            "styles": {
                "body": { "backgroundColor": "#FCF9F4" }
            }
        }
    }

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": user_id,
        "messages": [message]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body, headers=headers) as resp:
            print("Status:", resp.status)
            print("Body:", json.dumps(body, indent=2))
            print("Response:", await resp.text())


## 統整分析 (quick reply)
async def reply_analysis(reply_token: str):
    items = [{
        "type": "action",
        "action": {"type": "message", "label": f"{d} 天", "text": f"{d} 天"}
    } for d in (7, 30, 90)]
    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "text",
            "text": "請選擇統整分析時間：",
            "quickReply": {"items": items}
        }]
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        await session.post("https://api.line.me/v2/bot/message/reply", json=body, headers=headers)

async def reply_analysis_flex_menu(reply_token: str):
    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "flex",
            "altText": "請選擇統整分析期間",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "borderWidth": "4px",
                    "borderColor": "#FFE175",
                    "cornerRadius": "18px",
                    "contents": [
                        {
                            "type": "text",
                            "text": "請選擇統整分析區間",
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True
                        },
                        # {"type": "spacer", "size": "md"},
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "height": "10px" # 控制空白區塊高度
                        },
                        *[
                            {
                                "type": "button",
                                "action": { "type": "message", "label": f"最近 {d} 天", "text": f"分析最近 {d} 天的結果"},
                                "style": "secondary",
                                "height": "sm",
                                "margin": "md",
                                "color": "#FDEDC7"
                            }
                            for d in (7, 30, 90)
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

## 回覆分析結果
async def handle_analysis(reply_token: str, user_id: str, days: int):
    try:
        stats = analyze_checkins(user_id, days)
    except Exception:
        await reply_message(reply_token, "❌ 分析失敗，請稍後再試！")
        return

    # 1. 先把打卡統計拿出來
    bowls    = stats.get("bowls", 0)
    shops    = stats.get("shops", 0)
    top_shop = stats.get("top_shop", "無資料")
    flavor_pct = stats.get("flavor_pct", {})

    # 2. 準備「口味分布」列表（如果沒有資料，這裡就是空的）
    flavor_contents = []
    for flavor, pct in flavor_pct.items():
        flavor_contents.append({
            "type": "box",
            "layout": "baseline",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": flavor, "size": "sm", "weight": "bold", "flex": 1},
                {"type": "text", "text": pct,    "size": "sm", "align": "end"}
            ]
        })

    # 3. 準備 Bubble 的 body 主要內容
    body_contents = [
        {"type": "text", "text": f"最近 {days} 天的統整分析", "weight": "bold", "size": "lg"},
        # {"type": "spacer", "size": "md"},
        {"type": "box", "layout": "vertical", "contents": [], "height": "10px"},
        {"type": "text", "text": f"🍜 總碗數：{bowls} 碗", "size": "sm"},
        {"type": "text", "text": f"🏠 造訪店家：{shops} 家", "size": "sm"},
        {"type": "text", "text": f"⭐️ 最常吃：{top_shop}", "size": "sm", "margin": "md"},
        {"type": "separator", "margin": "md"},
    ]

    # 4. 當 bowls == 0（打卡為 0）時，不要放任何圖片，直接在 body_contents 加一行提示文字
    if bowls == 0:
        body_contents.append({
            "type": "text",
            "text": "🔒 打卡四張照片以上以解鎖拉麵 dump！",
            "size": "xs",
            # "align": "center",    
            "weight": "bold",
            "color": "#063D74",
            "margin": "md",
            "wrap": True,
            "maxLines": 2
        })

    # 5. 當 1 <= bowls < 4 時，雖然有打卡資料，但筆數不到 4，這裡顯示真正的圓餅圖＋鎖頭文字
    elif 1 <= bowls < 4:
        # 先產生圓餅圖 URL（create_quickchart_url 會正常產生有口味分布的圖）
        img_url = create_quickchart_url(flavor_pct)

        # 圖片
        body_contents.append({
            "type": "text", 
            "text": "口味分布", 
            "size": "sm", 
            "weight": "bold", 
            "margin": "md"
        })
        body_contents.append({
            "type": "box", 
            "layout": "vertical", 
            "spacing": "sm", 
            "contents": flavor_contents
        })
        body_contents.append({
            "type": "image",
            "url": img_url,
            "size": "full",
            "aspectRatio": "1:1",
            "aspectMode": "cover",
            "margin": "md"
        })

        # 再加一行紅色鎖頭文字
        body_contents.append({
            "type": "text",
            "text": "🔒 打卡四張照片以上以解鎖拉麵 dump！",
            "size": "xs",
            "weight": "bold",
            "color": "#063D74",
            "margin": "md",
            "wrap": True,
            "maxLines": 2
        })

    # 6. 當 bowls >= 4 時，顯示真正的圓餅圖＋按鈕（生成 4/6/12 格 dump）
    else:  # bowls >= 4
        img_url = create_quickchart_url(flavor_pct)

        # 圖片
        body_contents.append({
            "type": "text", 
            "text": "口味分布", 
            "size": "sm", 
            "weight": "bold", 
            "margin": "md"
        })
        body_contents.append({
            "type": "box", 
            "layout": "vertical", 
            "spacing": "sm", 
            "contents": flavor_contents
        })
        body_contents.append({
            "type": "image",
            "url": img_url,
            "size": "full",
            "aspectRatio": "1:1",
            "aspectMode": "cover",
            "margin": "md"
        })

        # 再 append 「生成我的拉麵 dump」這行文字
        body_contents.append({
            "type": "text",
            "text": "生成我的拉麵 dump",
            "weight": "bold",
            "size": "sm",
            "align": "center",
            "margin": "md"
        })

        # 最後再 extend 三個按鈕
        body_contents.extend([
            {
                "type": "button",
                "action": {"type": "message", "label": "生成 4 格 dump",  "text": "生成 4 格 dump"},
                "style": "secondary",
                "color": "#FDEDC7",
                "height": "sm",
                "margin": "sm"
            },
            {
                "type": "button",
                "action": {"type": "message", "label": "生成 6 格 dump",  "text": "生成 6 格 dump"},
                "style": "secondary",
                "color": "#FDEDC7",
                "height": "sm",
                "margin": "sm"
            },
            {
                "type": "button",
                "action": {"type": "message", "label": "生成 12 格 dump", "text": "生成 12 格 dump"},
                "style": "secondary",
                "color": "#FDEDC7",
                "height": "sm",
                "margin": "sm"
            }
        ])

    # 7. 把 body_contents 組成最終的 Flex Bubble
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "borderWidth": "4px",
            "borderColor": "#A9C4EB",
            "cornerRadius": "18px",
            "contents": body_contents,
        },
        "styles": {
            "body": { "backgroundColor": "#FCF9F4" }
        }
    }

    # 8. 回傳 Flex Message
    flex_message = {
        "replyToken": reply_token,
        "messages": [{"type": "flex", "altText": "統整分析結果", "contents": bubble}]
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        await session.post("https://api.line.me/v2/bot/message/reply", json=flex_message, headers=headers)


## 分析打卡紀錄內容
def analyze_checkins(user_id: str, days: int) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    docs = (
        db.collection('checkins')
          .where('user_id', '==', user_id)
          .order_by('timestamp', direction=firestore.Query.DESCENDING)
          .stream()
    )
    records = []
    shop_counter = Counter()
    keyword_counter = Counter()

    for doc in docs:
        data = doc.to_dict()
        ts = data.get('timestamp')
        if hasattr(ts, 'to_datetime'):
            ts = ts.to_datetime().replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            records.append(data)
            shop_counter[data.get('store_name', '未知商家')] += 1

            raw_kw = data.get('keyword', None)
            if raw_kw in FLAVORS:
                kw = raw_kw
            else:
                kw = "其他"
            keyword_counter[kw] += 1


    bowls = len(records)
    shops = len(shop_counter)
    top_shop = shop_counter.most_common(1)[0][0] if shop_counter else '尚無資料'

    # 使用打卡時傳入的 keyword 作為口味
    flavor_pct = {}
    if bowls:
        for kw, cnt in keyword_counter.items():
            pct = cnt / bowls * 100
            flavor_pct[kw] = f"{pct:.1f}%"

    print(f"[DEBUG] flavor_pct for user={user_id}, days={days}: {flavor_pct}")

    return {'bowls': bowls, 'shops': shops, 'top_shop': top_shop, 'flavor_pct': flavor_pct, 'records': records}

## 生成圓餅圖
def create_quickchart_url(flavor_pct: dict[str, str]) -> str:

    sorted_items = sorted(
        flavor_pct.items(),
        key=lambda kv: float(kv[1].strip('%')),  # kv = (label, "xx.x%")
        reverse=True
    )

    labels = [item[0] for item in sorted_items]
    sizes  = [float(item[1].strip('%')) for item in sorted_items]

    other_color = "#e3e3e3"
    palette = ["#d5e3f7", "#a9c4eb", "#8caedd", "#6a8cbb", "#ffd02c", "#ffdb5d", "#ffe699", "#fdf1c7"]
    bg_colors = []
    idx_palette = 0
    for flavor in labels:
        if flavor == "其他":
            bg_colors.append(other_color)
        else:
            color = palette[idx_palette % len(palette)]
            bg_colors.append(color)
            idx_palette += 1

    chart = {
        "type": "outlabeledPie",                   # ← 改成 outlabeledPie
        "data": {
            "labels": labels,
            "datasets": [{
                "data": sizes,
                "backgroundColor": bg_colors,
                "borderColor": "#ffffff",
                "borderWidth": 2
            }]
        },
        "options": {
            "layout": {
                "padding": {
                    "left": 40,
                    "right": 40,
                    "top": 20,
                    "bottom": 20
                }
            },
            "plugins": {
                "legend": False,
                "outlabels": {                       # ← 使用 outlabels plugin
                    "text": "%l %p",                # %l=label，%p=percent
                    "color": "black",
                    "stretch": 15,
                    "font": {
                        "resizable": True,
                        "minSize": 12,
                        "maxSize": 18
                    }
                }
            }
        }
    }

    base = "https://quickchart.io/chart"
    params = {
        "c": json.dumps(chart, ensure_ascii=False),
        "plugins": "chartjs-plugin-outlabels",     # ← 請載入 outlabels plugin
        "version": "2.9.4"                         # 範例是 v2.9.4，outlabels plugin 才能正常跑
    }
    return f"{base}?{urllib.parse.urlencode(params)}"

## 拉麵 dump 處理與回覆
async def handle_ramen_dump(
    reply_token: str,
    user_id: str,
    max_tiles: int | None = None
):
    days = user_last_days.get(user_id, 90)

    # 撈資料
    stats = analyze_checkins(user_id, days)
    records = stats.get("records", [])
    urls = [r["photo_url"] for r in records if r.get("photo_url")]
    if not urls:
        return await reply_message(reply_token, f"❌ 近 {days} 天內沒有可用的打卡照片啦～")
    
    if len(urls) < max_tiles:
        await push_message(
            user_id,
            {
                "type": "text",
                "text": f"❌ 需要至少 {max_tiles} 張照片才能生成「{max_tiles} 格 dump」，目前只有 {len(urls)} 張喔～"
            }
        )
        return

    # 只取前 max_tiles 張
    sliced = urls[:max_tiles]

    # 呼叫不變的 generate_ramen_dump
    dump_bytes = await generate_ramen_dump(sliced)

    # 上傳並回傳
    bucket = storage.bucket()
    suffix = f"_{max_tiles}tiles" if max_tiles else "_all"
    file_name = f"ramen_dump/{user_id}{suffix}_{uuid.uuid4().hex}.jpg"
    blob = bucket.blob(file_name)
    blob.upload_from_string(dump_bytes.getvalue(), content_type="image/jpeg")
    blob.make_public()
    public_url = blob.public_url

    img_message = {
        "type": "image",
        "originalContentUrl": public_url,   # 圖片原始網址
        "previewImageUrl": public_url       # 預覽圖網址，通常直接用原圖
    }
    await push_message(user_id, img_message)
    # await reply_image(reply_token, public_url)

GRID_LAYOUT = {
    4:  (2, 2),  # 2 列 × 2 排
    6:  (2, 3),  # 2 列 × 3 排
    12: (3, 4),  # 3 列 × 4 排
}

## 生成拉麵 dump 照片
async def generate_ramen_dump(
    urls: list[str],
    canvas_height: int = 1600,               # 直向畫布總高
    bg_color: tuple[int,int,int] = (0, 0, 0)  # 背景色
) -> io.BytesIO:
    # 這裡根據 urls 長度自动推 cols, rows （用 GRID_LAYOUT 或正方形 fallback）
    total = len(urls)
    cols, rows = GRID_LAYOUT.get(total, (
        int(math.sqrt(total)),
        math.ceil(total / int(math.sqrt(total)))
    ))

    # 建立 9:16 直向畫布
    canvas_h = canvas_height
    canvas_w = int(canvas_h * 9 / 16)
    tile_w = canvas_w // cols
    tile_h = canvas_h // rows
    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)

    for idx, url in enumerate(urls):
        resp = requests.get(url, timeout=10)
        img = Image.open(io.BytesIO(resp.content))
        img = ImageOps.exif_transpose(img).convert("RGB")
        thumb = ImageOps.fit(img, (tile_w, tile_h), method=Image.LANCZOS)

        x = (idx % cols) * tile_w
        y = (idx // cols) * tile_h
        canvas.paste(thumb, (x, y))

        img.close()

    bio = io.BytesIO()
    canvas.save(bio, format="JPEG", quality=90)
    bio.seek(0)
    return bio



@app.get("/check_location/{user_id}")
async def check_location_validity(user_id: str):
    is_valid, _ = await is_location_valid(user_id)
    return {"is_valid": is_valid}

class LocationUpdate(BaseModel):
    latitude: float
    longitude: float

@app.post("/update_location/{user_id}")
async def update_location_web(user_id: str, location: LocationUpdate):
    try:
        # 驗證輸入參數
        if not isinstance(location.latitude, (int, float)) or not isinstance(location.longitude, (int, float)):
            raise HTTPException(status_code=400, detail="Invalid latitude or longitude")
        
        # 驗證經緯度範圍
        if not (-90 <= location.latitude <= 90) or not (-180 <= location.longitude <= 180):
            raise HTTPException(status_code=400, detail="Latitude or longitude out of range")
            
        # 更新用戶位置
        update_user_location(user_id, location.latitude, location.longitude)
        return {"status": "success", "message": "Location updated successfully"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in update_location_web: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


