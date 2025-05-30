import firebase_admin
from datetime import datetime
import os
import json
from firebase_admin import credentials, firestore, initialize_app

cred = credentials.Certificate(r"C:\Users\User\Desktop\SAD\Web Crawler\key.json")
initialize_app(cred)
db = firestore.client()

# 讀取 JSON 檔案
json_path = r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\merge_json\merged_ramen_store_info.json"
with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

# 每間店寫入 Firestore 的 "ramen_shops" collection
for idx, item in enumerate(data, 1):  # 1開始
    store_name = item.get("name", "unknown").replace("/", "_")
    item['id'] = str(idx)  # 加入id，建議存字串比較不會有型別問題
    doc_ref = db.collection("ramen_shops").document(store_name)
    doc_ref.set(item)