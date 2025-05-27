import firebase_admin
from firebase_admin import credentials, storage
import os
import json

# 初始化 Firebase Admin（只執行一次）
cred = credentials.Certificate(r"C:\Users\User\Desktop\SAD\Web Crawler\key.json")
firebase_admin.initialize_app(cred, {
    "storageBucket": "la-king-man.firebasestorage.app"
})

# 圖片與 JSON 資料夾路徑
image_folder = r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\images"
json_folder = r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\json"

# 上傳圖片並更新對應 JSON
bucket = storage.bucket()
count = 0

for image_file in os.listdir(image_folder):
    if image_file.endswith("_menu.jpg"):
        # 去掉 _menu.jpg，找對應 json 檔案
        shop_prefix = image_file.replace("_menu.jpg", "")
        json_file = shop_prefix + ".json"

        image_path = os.path.join(image_folder, image_file)
        json_path = os.path.join(json_folder, json_file)

        # 如果 JSON 檔存在才處理
        if os.path.exists(json_path):
            print(f"🔄 處理 {image_file} -> {json_file}")

            # 上傳圖片
            firebase_path = f"menu_images/{image_file}"
            blob = bucket.blob(firebase_path)
            blob.upload_from_filename(image_path)
            blob.make_public()
            image_url = blob.public_url

            # 更新 JSON
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "store_info" in data:
                data["store_info"]["menu_image"] = image_url

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✅ 已更新：{json_file}")
                count += 1
        else:
            print(f"⚠️ 找不到對應 JSON：{json_file}")

print(f"\n✅ 全部完成，共更新 {count} 筆店家資料")
