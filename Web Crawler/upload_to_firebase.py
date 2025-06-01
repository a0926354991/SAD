import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# 初始化 Firestore
cred = credentials.Certificate(r"C:\Users\User\Desktop\SAD\Web Crawler\key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 讀取 JSON 檔
json_path = r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\merge_json\merged_ramen_store_info.json"
with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

# 將每家店寫到 ramen_stores，僅使用數字字串作為 Document ID
for idx, item in enumerate(data, 1):  # 從 1 開始編號
    # 下面這行不再把 id 存到 item 裡：
    # item['id'] = str(idx)

    # 改成直接把文件 ID 決定為 "1", "2", "3", …：
    doc_ref = db.collection("ramen_shops").document(str(idx))
    doc_ref.set(item)

    print(f"已寫入 ramen_shops/{idx}：名稱={item.get('name', '')}")
