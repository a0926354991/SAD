from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time, pandas as pd

url = "https://ifoodie.tw/explore/台北市/list/拉麵"

# 設定瀏覽器選項
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(url)
time.sleep(5)

# 滾動頁面幾次以載入更多店家
for _ in range(5):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

# 擷取所有店家卡片
cards = driver.find_elements(By.CSS_SELECTOR, 'a.restaurant-item')

records = []
for card in cards:
    try:
        name = card.find_element(By.CSS_SELECTOR, '.title').text.strip()
    except:
        name = ""
    try:
        address = card.find_element(By.CSS_SELECTOR, '.address-row').text.strip()
    except:
        address = ""
    try:
        rating = card.find_element(By.CSS_SELECTOR, '.rating').text.strip()
    except:
        rating = ""
    try:
        avg_price = card.find_element(By.CSS_SELECTOR, '.avg-price').text.strip()
    except:
        avg_price = ""
    
    link = card.get_attribute("href")
    
    records.append({
        "name": name,
        "address": address,
        "rating": rating,
        "avg_price": avg_price,
        "link": link
    })

driver.quit()

# 儲存為 CSV
df = pd.DataFrame(records)
df.to_csv(r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\台北拉麵_ifoodie_新版.csv", index=False, encoding="utf-8-sig")
print(f"✅ 已成功儲存 {len(df)} 筆資料到 CSV：台北拉麵_ifoodie_新版.csv")
