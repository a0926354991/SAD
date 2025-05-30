import firebase_admin
from datetime import datetime
import os
import json
from firebase_admin import credentials, firestore, initialize_app

cred = credentials.Certificate("key.json")
initialize_app(cred)
db = firestore.client()

# 讀取 JSON 檔案
with open("merged_ramen_store_info.json", encoding="utf-8") as f:
    data = json.load(f)

# 每間店寫入 Firestore 的 "ramen_shops" collection
for idx, item in enumerate(data, 1):  # 1開始
    doc_ref = db.collection("ramen_shops").document(str(idx))
    doc_ref.set(item)