import firebase_admin
from datetime import datetime
import os
import json
from firebase_admin import credentials, firestore, initialize_app

key_dict = json.loads(os.environ["FIREBASE_KEY_JSON"])
cred = credentials.Certificate(key_dict)

# 本機跑要開這行
# cred = credentials.Certificate("key.json")
initialize_app(cred)
db = firestore.client()
GeoPoint = firestore.GeoPoint

def add_user(line_user_id, display_name):
    user_ref = db.collection("users").document(line_user_id)
    user_ref.set({
        "display_name": display_name,
        "joined_at": datetime.utcnow()
    })

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
        "last_updated": firestore.SERVER_TIMESTAMP
    })

# if __name__ == "__main__":
#     shops = get_all_ramen_shops()
#     print(json.dumps(shops, ensure_ascii=False, indent=2))