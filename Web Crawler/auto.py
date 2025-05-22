from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

# 設定
MAX_SCROLLS      = 2   # 最多向下捲動幾次（原碼未使用，這裡正式啟用）
MAX_EXPAND_TRIES = 10   # 每輪 A 步驟最多嘗試點擊多少顆「展開」按鈕
SCROLL_PAUSE     = 2

# 啟動 WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    # 1. 開啟地點頁面
    driver.get(
        "https://www.google.com.tw/maps/place/MIMICO+COFFEE+%E7%A7%98%E5%AF%86%E5%AE%A2%E5%92%96%E5%95%A1%E9%A4%A8/@23.4836764,120.4450475,17z/data=!3m1!4b1!4m6!3m5!1s0x346e9426988bd085:0x25e91aa04e8f083e!8m2!3d23.4836716!4d120.4499184!16s%2Fg%2F11g_w5rkw?entry=ttu&g_ep=EgoyMDI1MDQzMC4xIKXMDSoASAFQAw%3D%3D")
    wait = WebDriverWait(driver, 10)
    # 等待「查看所有評論」按鈕出現並點擊
    try:
        more_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[jsaction="pane.reviewChart.moreReviews"]'))
        )
        more_btn.click()
        time.sleep(2)
    except Exception:
        pass

    # 3. 定位評論容器
    container = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde'))
    )

    # 4. 點擊「更多評論」直到載入完畢
    while True:
        try:
            btn = container.find_element(By.XPATH, './/button[contains(@jsaction, "moreReviews")]')
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1)
        except:
            break
    
    # ① 向下捲動 + 完整展開
    last_height = 0
    scroll_counter = 0               # ★ 新增：捲動次數計數器
    while scroll_counter < MAX_SCROLLS:
        # ---- A. 盡可能展開目前可見的長評 ----
        expand_tries = 0             # ★ 新增：本輪點擊次數
        while expand_tries < MAX_EXPAND_TRIES:
            expand_btns = container.find_elements(
                By.XPATH,
                './/button[@aria-expanded="false" and contains(@jsaction, ".review.expandReview")]'
            )
            if not expand_btns:
                break
            for btn in expand_btns:
                if expand_tries >= MAX_EXPAND_TRIES:
                    break            # 避免過度點擊
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", btn
                    )
                    WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable(btn)
                    )
                    btn.click()
                    expand_tries += 1
                    time.sleep(0.3)
                except Exception:
                    continue

        # ---- B. 再捲到底部載入新評論 ----
        driver.execute_script(
            "arguments[0].scrollTo(0, arguments[0].scrollHeight);", container
        )
        time.sleep(SCROLL_PAUSE)
        scroll_counter += 1           # ★ 更新捲動次數

        new_height = driver.execute_script(
            "return arguments[0].scrollHeight", container
        )
        if new_height == last_height:
            break                     # 沒有新評論 → 結束
        last_height = new_height


    # 新增步驟：點開所有「全文」按鈕

    # 6. 擷取所有評論文字（最多取前 20 筆）
    comments = container.find_elements(By.CSS_SELECTOR, 'span.wiI7pd')

    # 把 WebElement 轉成純 dict，再 dump 成 JSON
    comments_data = []
    for idx, elem in enumerate(comments[:20], start=1):
        comments_data.append({
            'id': idx,
            'text': elem.text  # 只擷取文字
        })

    # 7. 輸出到 JSON 檔
    file_name = "Web Crawler/Coffee Preview/MIMICO COFFEE.json"
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(comments_data, f, ensure_ascii=False, indent=2)

    print(f"已將 {len(comments_data)} 筆留言儲存到 {file_name}")
finally:
    driver.quit()
