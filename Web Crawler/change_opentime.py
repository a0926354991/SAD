import json
import os
import re

def clean_and_reorder_open_time(open_time_str: str) -> str:
    """
    1. 移除「營業時間可能不同.」和「隱藏本週營業時間」這兩個固定字串（如果存在）；
    2. 移除「星期五」等星期後的括號註記，例如 "(端午節 (補假))"；
    3. 將各段以「星期一」到「星期日」的順序重新排序；
    4. 回傳一個以“; ”分隔的乾淨 open_time 字串。
    """
    # 先把不需要的固定字串移除
    clean_str = open_time_str.replace("營業時間可能不同.", "").replace("隱藏本週營業時間", "").replace("假日營業時間", "").strip()

    # 定義星期對應的順序
    weekday_order = {
        "星期一": 1,
        "星期二": 2,
        "星期三": 3,
        "星期四": 4,
        "星期五": 5,
        "星期六": 6,
        "星期日": 7,
        "星期天": 7,  # 若使用「星期天」也視為週日
    }

    # 以分號拆成多個段落
    segments = [seg.strip() for seg in clean_str.split(";") if seg.strip()]

    cleaned_segments = []
    for seg in segments:
        # 1) 移除「星期X (任何括號)」中的括號註記，只保留「星期X」
        # 2) 保留逗號後面的所有時間描述內容
        parts = seg.split("、", 1)
        day_part = parts[0].strip()  # 例如 "星期五 (端午節 (補假))"
        rest = parts[1] if len(parts) > 1 else ""

        # 用正則擷取「星期X」作為乾淨的 day_clean
        m = re.match(r"^(星期[一二三四五六日天])", day_part)
        if m:
            day_clean = m.group(1)
        else:
            # 若無法匹配，就保留原樣
            day_clean = day_part

        # 如果 rest 裡面多了逗號或空格，可直接接回去
        cleaned_seg = f"{day_clean}、{rest}" if rest else day_clean
        cleaned_segments.append(cleaned_seg.strip())

    # 解析每段並標記排序依據
    parsed = []
    for seg in cleaned_segments:
        parts = seg.split("、", 1)
        day = parts[0].strip()
        order = weekday_order.get(day, 99)  # 找不到就排最後
        parsed.append((order, seg))

    # 按照星期順序排序
    parsed.sort(key=lambda x: x[0])

    # 組回一個完整字串，以「; 」隔開
    return "; ".join(seg for _, seg in parsed)


def process_shops_json(json_path: str):
    """
    讀取指定的 JSON 檔，假設最外層是一個 list，每個元素是單家店的 dict。
    對每一筆 shop["open_time"]：
      1. 移除「營業時間可能不同.」和「隱藏本週營業時間」；
      2. 移除星期之後的括號註記；
      3. 依「星期一」到「星期日」順序重新排序段落；
    如有修改，則覆寫回原檔案。
    """
    if not os.path.isfile(json_path):
        print(f"找不到檔案：{json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("錯誤：預期 JSON 檔最外層為 list，每個元素皆為店家資料的 dict。")
        return

    modified = False
    for shop in data:
        if not isinstance(shop, dict):
            continue
        if "open_time" in shop:
            original = shop["open_time"]
            new_open = clean_and_reorder_open_time(original)
            if new_open != original:
                shop["open_time"] = new_open
                modified = True

    if modified:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{os.path.basename(json_path)} 已更新所有店家的 open_time。")
    else:
        print(f"{os.path.basename(json_path)} 中的 open_time 已無需修改。")


if __name__ == "__main__":
    # 改成你實際的檔案路徑
    json_path = r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\merge_json\merged_ramen_store_info.json"
    process_shops_json(json_path)
