import os
import json

def merge_store_info(input_dir: str, output_file: str) -> None:
    '''
    讀取 input_dir 中所有 .json 檔，
    提取每個檔案中的 store_info，
    合併為一個 list 輸出到 output_file。
    '''
    merged_list = []

    for filename in os.listdir(input_dir):
        if not filename.lower().endswith('.json'):
            continue

        filepath = os.path.join(input_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                store_info = data.get("store_info")
                if store_info:
                    merged_list.append(store_info)
                else:
                    print(f"⚠️ {filename} 沒有 store_info，已跳過")
            except json.JSONDecodeError as e:
                print(f"⚠️ 無法解析 {filename}（{e}），已跳過。")
                continue

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_list, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    input_directory = 'Web Crawler/ramin/json'  # ✅ 改成你的拉麵 JSON 資料夾
    output_path = 'Web Crawler/ramin/merge_json/merged_ramen_store_info.json'
    merge_store_info(input_directory, output_path)
    print(f"✅ 已將所有 store_info 合併為列表並輸出到：{output_path}")
