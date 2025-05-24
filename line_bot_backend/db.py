import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

cred = credentials.Certificate("key.json")  # Firebase 的服務金鑰
firebase_admin.initialize_app(cred)
db = firestore.client()

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
