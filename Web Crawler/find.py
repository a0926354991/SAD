from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os, re, json, time, requests

# Google Maps URL
url = "https://www.google.com/maps/place/%E5%8D%81%E4%BA%8C%E5%B7%B7%E6%8B%89%E9%BA%B5/@25.0156951,121.5328123,17z/data=!3m1!4b1!4m6!3m5!1s0x3442a98ba212e0f5:0x8baecd4c6a3cc94e!8m2!3d25.0156951!4d121.5328123!16s%2Fg%2F11b7q2k0l3?entry=ttu&g_ep=EgoyMDI1MDUyMS4wIKXMDSoASAFQAw%3D%3D"

# 儲存資料夾
json_dir = "Web Crawler/ramin/json"
img_dir = "Web Crawler/ramin/images"
os.makedirs(json_dir, exist_ok=True)
os.makedirs(img_dir, exist_ok=True)

# 清理文字
def clean_text(text):
    return re.sub(r'[^\x00-\x7F\u4e00-\u9fff0-9\-()（）．:： ]+', '', text).strip()

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "", name)

# 啟動瀏覽器
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    time.sleep(5)

    store_info = {}

    # ✅ 店名
    try:
        store_info["name"] = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf'))).text
    except:
        store_info["name"] = ""
    
    short_name = sanitize_filename(store_info.get("name", "store")[:5])

    # ✅ 地址
    try:
        address = driver.find_element(By.XPATH, '//button[contains(@data-item-id,"address")]//div[contains(text(), "市")]')
        store_info["address"] = address.text.strip()
    except:
        store_info["address"] = ""

    # ✅ 電話
    try:
        phone_elem = driver.find_element(By.XPATH, '//button[contains(@data-item-id,"phone")]')
        store_info["phone"] = clean_text(phone_elem.text)
    except:
        store_info["phone"] = ""

    # 營業時間
    try:
        block = driver.find_element(By.XPATH, '//div[contains(@aria-label, "營業時間")]')
        store_info["open_time"] = block.get_attribute("aria-label")
    except:
        store_info["open_time"] = ""

    # 評分
    try:
        score = driver.find_element(By.CLASS_NAME, 'fontDisplayLarge')
        store_info["rating"] = float(score.text.strip())
    except:
        store_info["rating"] = None

    # 關鍵字（前3）
    try:
        keyword_buttons = driver.find_elements(By.CSS_SELECTOR, 'button.e2moi')
        keyword_pairs = []
        for btn in keyword_buttons:
            try:
                text = btn.find_element(By.CSS_SELECTOR, 'span.uEubGf.fontBodyMedium').text.strip()
                count = btn.find_element(By.CSS_SELECTOR, 'span.bC3Nkc.fontBodySmall').text.strip()
                count = int(re.sub(r"[^\d]", "", count))
                if text != "全部" and not text.startswith("+"):
                    keyword_pairs.append((text, count))
            except:
                continue
        top_keywords = sorted(keyword_pairs, key=lambda x: x[1], reverse=True)[:3]
        store_info["keywords"] = [kw[0] for kw in top_keywords]
    except:
        store_info["keywords"] = []

    # ✅ 從網址中提取座標
    try:
        match = re.search(r"!3d([0-9.]+)!4d([0-9.]+)", url)
        if match:
            lat = float(match.group(1))
            lng = float(match.group(2))
            store_info["latitude"] = lat
            store_info["longitude"] = lng
        else:
            store_info["latitude"] = None
            store_info["longitude"] = None
    except:
        store_info["latitude"] = None
        store_info["longitude"] = None

    # ✅ 點擊「全部評論」按鈕以進入完整評論頁
    try:
        all_reviews_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button[jsaction*="pane.reviewChart.moreReviews"]')))
        all_reviews_btn.click()
        time.sleep(3)
    except:
        print("⚠️ 找不到「全部評論」按鈕，可能無評論")

    # ✅ 滾動右側評論區（不是整頁！）
    try:
        scrollable_div = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR, 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf.ecceSd')))
        for _ in range(5):  # 可調整次數
            driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
            time.sleep(1.5)
    except:
        print("⚠️ 評論區滾動失敗")

    # ✅ 抓前幾則評論文字
    try:
        comment_blocks = driver.find_elements(By.CSS_SELECTOR, 'div.MyEned span.wiI7pd')
        comments = [c.text.strip() for c in comment_blocks if c.text.strip()]
        store_info["reviews"] = comments[:5]  # 限制最多 5 筆
    except:
        store_info["reviews"] = []

    # 菜單圖片（高解析度）
    try:
        img = driver.find_element(By.CSS_SELECTOR, 'img.DaSXdd')
        img_url = re.sub(r'=w\d+-h\d+-[^&]*', '=w1000-h1000', img.get_attribute("src"))
        img_path = os.path.join(img_dir, f"{short_name}_menu.jpg")
        with open(img_path, 'wb') as f:
            f.write(requests.get(img_url).content)
        store_info["menu_image"] = img_path
    except:
        store_info["menu_image"] = ""
    
    # 輸出成 JSON
    with open(os.path.join(json_dir, f"{short_name}.json"), 'w', encoding='utf-8') as f:
        json.dump({"store_info": store_info}, f, ensure_ascii=False, indent=2)

    print(f"✅ 成功儲存：{short_name}.json 和圖片")

finally:
    driver.quit()
