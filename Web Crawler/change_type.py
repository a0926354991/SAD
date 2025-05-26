import os
import json

# 自訂 GeoPoint 類（模擬 Firestore）
class GeoPoint:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

    def to_dict(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude
        }

# 資料夾路徑
folder_path = r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\json"

# 遍歷所有 JSON 檔案
for filename in os.listdir(folder_path):
    if filename.endswith(".json"):
        file_path = os.path.join(folder_path, filename)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            store = data.get("store_info", {})
            lat = store.pop("latitude", None)
            lng = store.pop("longitude", None)

            if lat is not None and lng is not None:
                store["location"] = GeoPoint(lat, lng).to_dict()

                # 覆蓋儲存回原檔案
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✅ 已轉換：{filename}")
            else:
                print(f"⚠️ 缺少經緯度欄位：{filename}")

        except Exception as e:
            print(f"❌ 轉換失敗：{filename}，錯誤：{e}")
