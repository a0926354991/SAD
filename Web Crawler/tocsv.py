import pandas as pd
import json
import glob

# 設定 JSON 檔案所在的資料夾路徑
json_files = glob.glob(r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\json*.json")

# 儲存所有資料
all_data = []

# 讀取每一個 JSON 檔案
for file in json_files:
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, list):
            all_data.extend(data)  # 如果是 list of dicts
        elif isinstance(data, dict):
            all_data.append(data)  # 如果是一個 dict

# 轉換成 DataFrame
df = pd.DataFrame(all_data)

# 儲存成 CSV
df.to_csv("merged_output.csv", index=False, encoding='utf-8-sig')
