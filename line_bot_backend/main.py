from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from dotenv import load_dotenv
from line_bot_backend.db import db, add_user, get_all_ramen_shops, get_user_by_id, update_user_location, get_user_location, search_ramen_nearby, create_checkin, upload_photo, get_store_checkins
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
UPLOAD_KEYWORDS = ["打卡","打卡上傳", "照片上傳"]
ANALYSIS_KEYWORDS = ["統整", "分析", "統整分析"]
FEEDBACK_KEYWORDS = ["意見回饋", "回饋"]
FLAVORS = ["豚骨", "醬油", "味噌", "鹽味", "辣味", "雞白湯", "海老", "魚介"]
# DUMP_KEYWORDS = ["生成我的拉麵 dump", "拉麵 dump", "拉麵 Dump", "拉麵dump", "拉麵Dump", "dump", "Dump"]

# 儲存使用者位置（之後要改用 Firestore，現在先這樣）
user_locations = {}
user_last_days: dict[str,int] = {}
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
                    await reply_analysis(reply_token)

                elif msg in ["7天", "30天", "90天"]:
                    days = int(msg.replace("天", ""))
                    await handle_analysis(reply_token, user_id, days)

                elif msg == "生成 4 格 dump":
                    await handle_ramen_dump(reply_token, user_id, max_tiles=4)
                elif msg == "生成 6 格 dump":
                    await handle_ramen_dump(reply_token, user_id, max_tiles=6)
                elif msg == "生成 12 格 dump":
                    await handle_ramen_dump(reply_token, user_id, max_tiles=12)
                
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
                            # ids_str = ",".join(shop_ids)
                            encoded_store_ids = quote(",".join(shop_ids))
                            roulette_url = f"https://liff.line.me/2007489792-4popYn8a#show_wheel=1&store_ids={encoded_store_ids}"
                            
                            # message = {
                            #     "type": "template",
                            #     "altText": "點擊「轉一下！」進入拉麵轉盤",
                            #     "template": {
                            #         "type": "buttons",
                            #         "title": "拉麵轉盤",
                            #         "text": "🎲 沒辦法決定要吃哪一家嗎？",
                            #         "actions": [
                            #             {
                            #                 "type": "uri",
                            #                 "label": "轉一下！",   # 你要顯示的文字
                            #                 "uri": roulette_url   # 你要跳的網址
                            #             }
                            #         ]
                            #     }
                            # }

                            # 傳一個訊息給使用者
                            reply_text = f"🎲 沒辦法決定要吃哪一家嗎？點這裡進入轉盤\n{roulette_url}"
                            await push_message(user_id, reply_text)
                            # await push_template(user_id, message)
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

#### Reply message or push message
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
        "messages": [{"type": "text", "text": message}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body, headers=headers) as resp:
            print("Status:", resp.status)
            print("Body:", json.dumps(body, indent=2))
            print("Response:", await resp.text())

async def push_template(user_id, message):
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
                            "uri": f"https://liff.line.me/2007489792-4popYn8a#store_id={ramen['id']}"
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


async def reply_analysis(reply_token: str):
    items = [{
        "type": "action",
        "action": {"type": "message", "label": f"{d}天", "text": f"{d}天"}
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


async def handle_analysis(reply_token: str, user_id: str, days: int):
    try:
        stats = analyze_checkins(user_id, days)
    except Exception:
        await reply_message(reply_token, "❌ 分析失敗，請稍後再試！")
        return

    # 計算最常吃店家
    top_shop = stats.get('top_shop', '無資料')

    # 生成圓餅圖並上傳
    img_url = create_quickchart_url(stats["flavor_pct"])
    print("QuickChart URL:", img_url)

    # 建立 Flex Bubble
    flavor_contents = []
    for flavor, pct in stats['flavor_pct'].items():
        flavor_contents.append({
            "type": "box", "layout": "baseline", "spacing": "md", "contents": [
                {"type": "text", "text": flavor, "size": "sm", "weight": "bold", "flex": 1},
                {"type": "text", "text": pct, "size": "sm", "align": "end"}
            ]
        })

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"近 {days} 天統整分析", "weight": "bold", "size": "lg"},
                {"type": "separator", "margin": "sm"},
                {"type": "text", "text": f"🍜 總碗數：{stats['bowls']} 碗", "size": "sm"},
                {"type": "text", "text": f"🏠 造訪店家：{stats['shops']} 家", "size": "sm"},
                {"type": "text", "text": f"⭐️ 最常吃：{top_shop}", "size": "sm", "margin": "md"},
                {"type": "text", "text": "口味分布", "size": "sm", "weight": "bold", "margin": "md"},
                {"type": "box", "layout": "vertical", "spacing": "sm", "contents": flavor_contents},
                {
                    "type": "image",
                    "url": img_url,
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover",
                    "margin": "md"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "生成我的拉麵 dump",
                    "weight": "bold",
                    "size": "sm",
                    "align": "center",
                    "margin": "md"
                },
                {
                    "type": "button",
                    "action": {"type": "message", "label": "生成 4 格 dump",  "text": "生成 4 格 dump"},
                    "style": "secondary",
                    "color": "#CCCCCC",
                    "height": "sm",
                    "margin": "sm"
                },
                {
                    "type": "button",
                    "action": {"type": "message", "label": "生成 6 格 dump",  "text": "生成 6 格 dump"},
                    "style": "secondary",
                    "color": "#CCCCCC",
                    "height": "sm",
                    "margin": "sm"
                },
                {
                    "type": "button",
                    "action": {"type": "message", "label": "生成 12 格 dump", "text": "生成 12 格 dump"},
                    "style": "secondary",
                    "color": "#CCCCCC",
                    "height": "sm",
                    "margin": "sm"
                }
            ]
        }
    }

    flex_message = {
        "replyToken": reply_token,
        "messages": [{"type": "flex", "altText": "統整分析結果", "contents": bubble}]
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        await session.post("https://api.line.me/v2/bot/message/reply", json=flex_message, headers=headers)


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
            # 統計店家
            shop_counter[data.get('store_name', '未知商家')] += 1
            # 統計關鍵字作為口味
            kw = data.get('keyword', '其他')
            keyword_counter[kw] += 1

    bowls = len(records)
    shops = len(shop_counter)
    top_shop = shop_counter.most_common(1)[0][0] if shop_counter else '無資料'

    # 使用打卡時傳入的 keyword 作為口味
    flavor_pct = {}
    if bowls:
        for kw, cnt in keyword_counter.items():
            pct = cnt / bowls * 100
            flavor_pct[kw] = f"{pct:.1f}%"

    return {'bowls': bowls, 'shops': shops, 'top_shop': top_shop, 'flavor_pct': flavor_pct, 'records': records}


def create_quickchart_url(flavor_pct: dict[str, str]) -> str:
    if not flavor_pct:
        raise ValueError("flavor_pct is empty or None")

    labels = list(flavor_pct.keys())
    sizes  = [float(p.strip('%')) for p in flavor_pct.values()]

    other_color = "#e3e3e3"
    palette = ["#6a8cbb", "#8caedd", "#a9c4eb", "#d5e3f7", "#ffdb5d", "#ffe699", "#fdf1c7"]
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
        "type": "pie",
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
            "plugins": {
                "datalabels": {
                    "display": True,
                    # 用 __raw 字段注入 JS function
                    "formatter": {
                        "__raw": "function(ctx) { return ctx.chart.data.labels[ctx.dataIndex]; }"
                    },
                    "color": "#ffffff",
                    "font": {"size": 16, "weight": "bold"}
                },
                # 2.2 取消默认的 legend/tooltip
                "legend": {"display": False},
                "title":  {"display": False},
                "tooltip": {"enabled": False}
            }
        }
    }

    base = "https://quickchart.io/chart"
    params = {
        "c": json.dumps(chart, ensure_ascii=False),
        "plugins": "chartjs-plugin-datalabels"
    }
    return f"{base}?{urllib.parse.urlencode(params)}"


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

    await reply_image(reply_token, public_url)


GRID_LAYOUT = {
    4:  (2, 2),  # 2 列 × 2 排
    6:  (2, 3),  # 2 列 × 3 排
    12: (3, 4),  # 3 列 × 4 排
}


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


async def reply_image(reply_token: str, image_url: str):
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





