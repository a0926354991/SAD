import json
import os
import re

def clean_and_reorder_open_time(open_time_str: str) -> str:
    """
    執行以下步驟處理 open_time 字串：
    1. 移除「營業時間可能不同.」、「隱藏本週營業時間」和「假日營業時間」等固定文字（若存在）。
    2. 將每段多餘的尾部頓號（"、"）或句點去掉。
    3. 把「星期X、」中第一個頓號換成冒號，並確保每天若有多個營業區間，用頓號「、」分隔，而不是再次用「：」。
       例如：「星期五、11:00 到 20:30、17:00 到 22:00」→「星期五：11:00 到 20:30、17:00 到 22:00」
    4. 移除「星期X (任何括號註記)」中的括號，只保留「星期X」本身。
    5. 若某段開頭有多餘的標點（如 .、、），一併去掉。
    6. 依「星期一」到「星期日」順序把各段排序。
    7. 以 "; " 重新串接所有段落並回傳乾淨字串。
    """
    # 先移除不需要的固定文字
    clean_str = (
        open_time_str
        .replace("營業時間可能不同.", "")
        .replace("隱藏本週營業時間", "")
        .replace("假日營業時間", "")
        .strip()
    )

    # 星期對照排序順序
    weekday_order = {
        "星期一": 1,
        "星期二": 2,
        "星期三": 3,
        "星期四": 4,
        "星期五": 5,
        "星期六": 6,
        "星期日": 7,
        "星期天": 7,
    }

    # 切分成多段
    segments = [seg.strip() for seg in clean_str.split(";") if seg.strip()]
    cleaned_segments = []

    for seg in segments:
        # Step 5: 去掉開頭多餘標點（如 .、、）
        seg = re.sub(r'^[\s\.,、]+', '', seg)

        # Step 2: 去除段尾多餘的頓號或句點
        seg = re.sub(r'[、\.]+$', '', seg).strip()

        # Step 3: 把「星期X、」中的第一個頓號換成冒號
        # 先確認存在頓號，並且該頓號出現在「星期X」之後
        if "、" in seg:
            left, right = seg.split("、", 1)
            seg = f"{left}：{right}"

        # Step 4: 移除「星期X (任何括號註記)」中的括號，只保留「星期X」
        # 先以冒號分段
        parts = seg.split("：", 1)
        day_part = parts[0].strip()        # 例如 "星期五 (端午節 (補假))"
        rest_time = parts[1] if len(parts) > 1 else ""

        m = re.match(r"^(星期[一二三四五六日天])", day_part)
        if m:
            day_clean = m.group(1)        # 取得乾淨的「星期五」
        else:
            day_clean = day_part          # 若不符合預期，保留原樣

        # Step 3 (續): 如果 rest_time 裡面多了第二個「：」，它其實是多時段的分隔，應該換成頓號「、」
        if rest_time and "：" in rest_time:
            # 只把 rest_time 裡的第一個「：」換成「、」
            rest_time = rest_time.replace("：", "、", 1)

        # 重組這一段：若有時間描述，就用「星期X：時間描述」
        if rest_time:
            cleaned_seg = f"{day_clean}：{rest_time.strip()}"
        else:
            cleaned_seg = day_clean

        cleaned_segments.append(cleaned_seg)

    # 排序
    parsed = []
    for seg in cleaned_segments:
        day = seg.split("：", 1)[0].strip()
        order = weekday_order.get(day, 99)
        parsed.append((order, seg))

    parsed.sort(key=lambda x: x[0])

    return "; ".join(seg for _, seg in parsed)


def process_shops_json(json_path: str):
    """
    讀取指定的 JSON 檔，假設最外層為 list，每個元素為單家店的 dict。
    對每家 shop["open_time"]：
      - 移除不必要文字、換頓號／冒號、刪除括號註記等，
      - 將多時段確保用頓號分隔，
      - 最後依照星期排序並串回字串。
    如有變動，則覆寫回原檔案。
    """
    if not os.path.isfile(json_path):
        print(f"找不到檔案：{json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("錯誤：預期 JSON 檔最外層為 list，每個元素為店家資訊 dict。")
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
    # 請替換成你的實際檔案路徑
    json_path = r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\merge_json\merged_ramen_store_info.json"
    process_shops_json(json_path)
