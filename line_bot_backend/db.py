import os
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage, initialize_app
from google.cloud.firestore_v1.base_document import DocumentSnapshot
import math
import uuid

key_dict = json.loads(os.environ["FIREBASE_KEY_JSON"])
cred = credentials.Certificate(key_dict)

# 本機跑要開這行
# cred = credentials.Certificate("key.json")

initialize_app(cred, {
    "storageBucket": "la-king-man.firebasestorage.app"
})
db = firestore.client()
bucket = storage.bucket()
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
            "joined_at": datetime.now(),
            "latlng": GeoPoint(0, 0),
            "last_updated": datetime.now(),
            "selected_ramen_shops": list(),
        })
        return True

def record_checkin(line_user_id, ramen_store):
    checkin_ref = db.collection("checkins").document()
    checkin_ref.set({
        "line_user_id": line_user_id,
        "ramen_store": ramen_store,
        "timestamp": datetime.now()
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
        # shop["id"] = doc.id
        result.append(shop)
    return result

## 毛加的，linebot 要用
def update_user_location(user_id: str, lat: float, lng: float):
    user_ref = db.collection("users").document(user_id)
    user_ref.update({
        "latlng": GeoPoint(lat, lng),
        "last_updated": datetime.now(),
    })

def get_user_location(user_id: str):
    user_ref = db.collection("users").document(user_id)
    doc = user_ref.get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("latlng"), data.get("last_updated")
    return None, None

def search_ramen_nearby(lat, lng, flavor):
    """
    搜尋附近的拉麵店
    Args:
        lat: 緯度
        lng: 經度
        flavor: 拉麵口味，如果為 None 則搜尋所有口味
    Returns:
        list: 附近的拉麵店列表，按距離排序
    """
    try:
        # 根據是否有指定口味來建立查詢
        if flavor:
            docs = db.collection("ramen_shops").where("keywords", "array_contains", flavor).stream()
        else:
            docs = db.collection("ramen_shops").stream()
        
        shops = []
        for doc in docs:
            try:
                data = doc.to_dict()
                location = data.get("location", {})
                
                # 檢查必要的位置資料
                if not location or "latitude" not in location or "longitude" not in location:
                    print(f"Warning: Store {doc.id} has invalid location data")
                    continue
                
                shop_lat = location["latitude"]
                shop_lng = location["longitude"]
                dist = haversine(lat, lng, shop_lat, shop_lng)
                
                shops.append({
                    "id": doc.id,
                    "name": data.get("name", ""),
                    "distance": dist,
                    "address": data.get("address", ""),
                    "image_url": data.get("picture_image", ""),
                    "rating": data.get("rating", 0),
                    "phone": data.get("phone", ""),
                    "lat": shop_lat,
                    "lng": shop_lng,
                    "keywords": data.get("keywords", []),
                    "location": location,
                    "open_time": data.get("open_time", ""),
                    "menu_image": data.get("menu_image", "")
                })
                
            except Exception as e:
                print(f"Error processing store {doc.id}: {str(e)}")
                continue
        
        # 按照距離排序
        shops.sort(key=lambda x: x["distance"])
        return shops
        
    except Exception as e:
        print(f"Error in search_ramen_nearby: {str(e)}")
        return []

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
        latlng = data.get("latlng")
        return {
            "id": doc.id,
            "display_name": data.get("display_name", ""),
            "joined_at": data.get("joined_at", ""),
            "last_updated": data.get("last_updated", ""),
            "latlng": {
                "latitude": round(latlng.latitude, 6) if latlng else None,
                "longitude": round(latlng.longitude, 6) if latlng else None
            } if latlng else None
        }
    return None

def create_checkin(data: dict):
    try:
        store_id = data.get("store_id")
        user_id = data.get("user_id")
        rating = data.get("rating")
        comment = data.get("comment", "")
        photo_url = data.get("photo_url", "")

        # 檢查必要欄位
        if not store_id or not user_id or rating is None:
            return False, "Missing required field(s)"

        # 取得店家資訊
        store_ref = db.collection("ramen_shops").document(store_id)
        store_doc = store_ref.get()
        if not store_doc.exists:
            return False, "Store not found"
        store_data = store_doc.to_dict()

        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return False, "User not found"
        user_data = user_doc.to_dict()

        # 建立打卡記錄
        checkin_data = {
            "store_id": store_data.get("id", ""),
            "store_name": store_data.get("name", ""),
            "user_id": user_id,
            "user_name": user_data.get("display_name", ""),
            "rating": rating,
            "comment": comment,
            "photo_url": photo_url,
            "timestamp": datetime.now()
        }

        checkin_ref = db.collection("checkins").document()
        checkin_ref.set(checkin_data)

        return True, "Check-in recorded successfully"
    except Exception as e:
        return False, str(e)

def upload_photo(file_content: bytes, content_type: str) -> tuple[bool, str]:
    """
    上傳照片到 Firebase Storage
    Returns:
        tuple[bool, str]: (成功與否, URL或錯誤訊息)
    """
    try:
        # 生成唯一檔名
        file_extension = '.jpg' if 'jpeg' in content_type else '.png'
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # 設定 Firebase Storage 路徑
        bucket = storage.bucket()
        blob = bucket.blob(f"checkin_photos/{unique_filename}")
        
        # 上傳檔案到 Firebase Storage
        blob.upload_from_string(
            file_content,
            content_type=content_type
        )
        
        # 設定檔案為公開可讀
        blob.make_public()
        
        return True, blob.public_url
    except Exception as e:
        return False, str(e)



# if __name__ == "__main__":
#     shops = get_all_ramen_shops()
#     print(json.dumps(shops, ensure_ascii=False, indent=2))