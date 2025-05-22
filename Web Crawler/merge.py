import os
import json

def merge_json_files(input_dir: str, output_file: str) -> None:
    '''
    讀取 input_dir 中所有 .json 檔，
    以檔名（不含 .json）為 key，檔案內容為 value，
    最後輸出到 output_file。
    '''
    
    merged = {}

    # 遍歷資料夾中所有檔案
    for filename in os.listdir(input_dir):
        if not filename.lower().endswith('.json'):
            continue

        filepath = os.path.join(input_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"警告：無法解析 {filename}（{e}），已跳過。")
                continue

        # 以不含副檔名的檔名作為 key
        key = os.path.splitext(filename)[0]
        merged[key] = data

    # 將合併後的 dict 寫入新的 JSON 檔
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    input_directory = 'Web Crawler/Coffee Preview'
    output_path = 'merged_coffee_preview.json'
    merge_json_files(input_directory, output_path)
    print(f"已將所有 JSON 合併並輸出到 {output_path}")
