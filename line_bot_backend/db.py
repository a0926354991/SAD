import os
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore_v1.base_document import DocumentSnapshot
import math

key_dict = json.loads(os.environ["FIREBASE_KEY_JSON"])
cred = credentials.Certificate(key_dict)

# 本機跑要開這行
# cred = credentials.Certificate("key.json")
initialize_app(cred)
db = firestore.client()
GeoPoint = firestore.GeoPoint

def add_user(line_user_id, display_name):
    user_ref = db.collection("users").document(line_user_id)
    doc = user_ref.get()
    if isinstance(doc, DocumentSnapshot) and doc.exists:
        # 已存在就不處理
        return False
    else:
        # 不存在才新增
        user_ref.set({
            "display_name": display_name,
            "joined_at": datetime.utcnow(),
            "latlng": GeoPoint(0, 0),
            "last_updated": datetime.utcnow(),
        })
        return True

def record_checkin(line_user_id, ramen_store):
    checkin_ref = db.collection("checkins").document()
    checkin_ref.set({
        "line_user_id": line_user_id,
        "ramen_store": ramen_store,
        "timestamp": datetime.utcnow()
    })

def add_ramen_store(store_id, name, location):
    store_ref = db.collection("ramen_stores").document(store_id)
    store_ref.set({
        "name": name,
        "location": location
    })

def get_all_ramen_shops():
    docs = db.collection("ramen_shops").stream()
    result = []
    for doc in docs:
        shop = doc.to_dict()
        shop["id"] = doc.id
        result.append(shop)
    return result

## 毛加的，linebot 要用
def update_user_location(user_id: str, lat: float, lng: float):
    user_ref = db.collection("users").document(user_id)
    user_ref.update({
        "latlng": GeoPoint(lat, lng),
        "last_updated": datetime.utcnow(),
    })

def get_user_location(user_id: str):
    user_ref = db.collection("users").document(user_id)
    doc = user_ref.get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("latlng"), data.get("last_updated")
    return None, None

def search_ramen_nearby(lat, lng, flavor):
    # 取得所有有該 flavor 的拉麵店
    docs = db.collection("ramen_shops").where("keywords", "array_contains", flavor).stream()
    
    shops = []
    for doc in docs:
        data = doc.to_dict()
        shop_lat = data["location"]["latitude"]
        shop_lng = data["location"]["longitude"]
        dist = haversine(lat, lng, shop_lat, shop_lng)
        shops.append({
            "id": data.get("id", ""),
            "name": data.get("name", ""),
            "distance": dist,
            "address": data.get("address", ""),
            "image_url": data.get("menu_image", ""),
            "rating": data.get("rating", 0),
            "phone": data.get("phone", ""),
            "lat": shop_lat,
            "lng": shop_lng,
            "keywords": data.get("keywords", []),
        })
    # 按照距離排序
    shops.sort(key=lambda x: x["distance"])
    return shops

def haversine(lat1, lng1, lat2, lng2):
    # Haversine formula
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def get_user_by_id(user_id: str):
    user_ref = db.collection("users").document(user_id)
    doc = user_ref.get()
    if doc.exists:
        data = doc.to_dict()
        return {
            "id": doc.id,
            "display_name": data.get("display_name", ""),
            "joined_at": data.get("joined_at", ""),
            "last_updated": data.get("last_updated", "")
        }
    return None

def create_checkin(data: dict):
    try:
        store_id = data.get("store_id")
        user_id = data.get("user_id")
        rating = data.get("rating")
        comment = data.get("comment", "")

        # 檢查必要欄位
        if not store_id or not user_id or rating is None:
            return False, "Missing required field(s)"

        # 取得店家資訊
        store_ref = db.collection("ramen_shops").document(store_id)
        store_doc = store_ref.get()
        if not store_doc.exists:
            return False, "Store not found"
        store_data = store_doc.to_dict()

        # 建立打卡記錄
        checkin_data = {
            "store_id": store_id,
            "store_name": store_data.get("name", ""),
            "user_id": user_id,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.utcnow()
        }

        checkin_ref = db.collection("checkins").document()
        checkin_ref.set(checkin_data)

        return True, "Check-in recorded successfully"
    except Exception as e:
        return False, str(e)

# if __name__ == "__main__":
#     shops = get_all_ramen_shops()
#     print(json.dumps(shops, ensure_ascii=False, indent=2))