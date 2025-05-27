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
    if image_file.endswith("_picture.jpg"):
        shop_prefix = image_file.replace("_picture.jpg", "")
        json_file = shop_prefix + ".json"

        image_path = os.path.join(image_folder, image_file)
        json_path = os.path.join(json_folder, json_file)

        if os.path.exists(json_path):
            print(f"🔄 處理 {image_file} -> {json_file}")

            # 上傳圖片
            firebase_path = f"menu_images/{image_file}"
            blob = bucket.blob(firebase_path)
            blob.upload_from_filename(image_path)
            blob.make_public()
            picture_url = blob.public_url

            # 更新 JSON
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "store_info" in data:
                # 插入 picture_image 在 menu_image 後面（保順序）
                new_store_info = {}
                for key, value in data["store_info"].items():
                    new_store_info[key] = value
                    if key == "menu_image":
                        new_store_info["picture_image"] = picture_url
                data["store_info"] = new_store_info

                # 儲存更新後的 JSON
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✅ 已更新：{json_file}")
                count += 1
        else:
            print(f"⚠️ 找不到對應 JSON：{json_file}")

print(f"\n✅ 全部完成，共更新 {count} 筆店家資料")
