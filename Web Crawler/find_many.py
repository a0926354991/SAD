from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os, re, json, time, requests

# ✅ 多個 Google Maps URL（可自行擴充）
url_list = [
    # url
]

# 資料夾
json_dir = "Web Crawler/ramin/json"
img_dir = "Web Crawler/ramin/images"
os.makedirs(json_dir, exist_ok=True)
os.makedirs(img_dir, exist_ok=True)

def clean_text(text):
    return re.sub(r'[^\x00-\x7F\u4e00-\u9fff0-9\-()（）．:： ]+', '', text).strip()

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "", name)

# 啟動瀏覽器
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

try:
    for url in url_list:
        try:
            driver.get(url)
            time.sleep(5)

            store_info = {}

            # 店名
            try:
                store_info["name"] = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf'))).text
            except:
                store_info["name"] = ""
            
            short_name = sanitize_filename(store_info.get("name", "store")[:5])

            # 地址
            try:
                address = driver.find_element(By.XPATH, '//button[contains(@data-item-id,"address")]//div[contains(text(), "市")]')
                store_info["address"] = address.text.strip()
            except:
                store_info["address"] = ""

            # 電話
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

            # 關鍵字
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

            # 菜單圖片
            try:
                img = driver.find_element(By.CSS_SELECTOR, 'img.DaSXdd')
                img_url = re.sub(r'=w\d+-h\d+-[^&]*', '=w1000-h1000', img.get_attribute("src"))
                img_path = os.path.join(img_dir, f"{short_name}_menu.jpg")
                with open(img_path, 'wb') as f:
                    f.write(requests.get(img_url).content)
                store_info["menu_image"] = img_path
            except:
                store_info["menu_image"] = ""

            # 輸出 JSON
            with open(os.path.join(json_dir, f"{short_name}.json"), 'w', encoding='utf-8') as f:
                json.dump({"store_info": store_info}, f, ensure_ascii=False, indent=2)

            print(f"✅ 成功儲存：{short_name}.json 和圖片")

        except Exception as e:
            print(f"❌ 抓取 {url} 失敗：{e}")

finally:
    driver.quit()
