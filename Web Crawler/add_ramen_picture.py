import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import os

# Excel 路徑與圖片儲存資料夾
excel_path = r"C:\Users\User\Desktop\SAD\Web Crawler\Start research.xlsx"
save_dir = r"C:\Users\User\Desktop\SAD\Web Crawler\ramin\images"
os.makedirs(save_dir, exist_ok=True)

# 讀取 Excel 資料
df = pd.read_excel(excel_path, sheet_name="add")

# 設定瀏覽器選項
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # 無頭模式
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# 啟動瀏覽器
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 逐筆抓圖
for idx, row in df.iterrows():
    name = str(row['店名'])[:7] 
    url = row['網址']
    
    try:
        print(f"正在處理：{name} - {url}")
        driver.get(url)
        time.sleep(5)  # 等待載入

        image = driver.find_element(By.CSS_SELECTOR, 'img[src^="https://lh3.googleusercontent.com"]')
        img_url = image.get_attribute('src')
        
        response = requests.get(img_url)
        filename = f"{name}_picture.jpg"
        filepath = os.path.join(save_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)

        print(f"→ 成功下載：{filename}")

    except Exception as e:
        print(f"✘ 下載失敗：{name}，錯誤：{e}")

# 關閉瀏覽器
driver.quit()
