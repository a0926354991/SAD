# 拉麵地圖系統（Ramen Map System）

## 目錄結構總覽

```
├── frontend/                # 前端專案（地圖、意見回饋）
│   ├── ramen-map/           # 主地圖前端（純 JS + Google Maps）
│   └── feedback/            # 意見回饋頁面（Firebase 寫入）
├── line_bot_backend/        # FastAPI 後端 + LINE Bot + Firebase
├── Web Crawler/             # Google Maps 拉麵店爬蟲與資料處理
│   └── ramin/               # 爬蟲產生的 json、圖片等
├── render.yaml              # Render 雲端部署設定
├── package.json             # 根目錄 JS 依賴（Google Maps 標記聚合）
└── ...
```

---

## 系統架構說明

### 1. 前端（frontend/ramen-map）
- **功能**：
  - 顯示台灣拉麵店地圖（Google Maps）
  - 搜尋、篩選、查看店家資訊
  - 用戶登入（LINE OAuth）、打卡、評論、拉麵轉盤推薦
  - 查看個人打卡紀錄
- **技術棧**：
  - 原生 JavaScript、HTML、CSS
  - Google Maps JavaScript API
  - Firebase（用於登入、資料同步）
  - 與 FastAPI 後端 API 串接
- **啟動方式**：
  - `cd frontend/ramen-map && npm install && npm start`
  - 以 `serve .` 啟動本地伺服器

### 2. 意見回饋（frontend/feedback）
- **功能**：
  - 用戶可填寫意見回饋，直接寫入 Firebase Firestore
- **技術棧**：
  - 單頁 HTML + JS，直接用 Firebase Web SDK

### 3. 後端 API 與 LINE Bot（line_bot_backend）
- **功能**：
  - FastAPI 提供 RESTful API，支援：
    - 拉麵店查詢、附近店家、用戶登入/資訊、打卡、評論、照片上傳
    - LINE Bot webhook，支援用戶互動、推播、分析、拉麵轉盤等
    - 與 Firebase Firestore/Storage 整合
- **技術棧**：
  - Python 3.10+
  - FastAPI、Uvicorn、SQLAlchemy、firebase-admin、line-bot-sdk
  - Firebase（Firestore/Storage）
- **啟動方式**：
  - `cd line_bot_backend && pip install -r requirements.txt`
  - `uvicorn main:app --reload --port 10000`
- **部署**：
  - 參考 `render.yaml`，可用 Render 雲端自動部署

### 4. 爬蟲與資料處理（Web Crawler）
- **功能**：
  - 使用 Selenium 自動化爬取 Google Maps 拉麵店資訊
  - 產生 json 檔、圖片，供主系統匯入
  - 支援批次爬取（Excel 輸入）
- **技術棧**：
  - Python、Selenium、webdriver-manager、pandas
- **啟動方式**：
  - 需安裝 Chrome Driver
  - `python find.py` 或 `python find_many.py`

---

## 主要資料流與整合

1. **資料來源**：
   - 由 `Web Crawler` 爬取 Google Maps，產生 json 與圖片
   - 匯入 Firebase Firestore/Storage，成為主資料庫
2. **後端 API**：
   - FastAPI 提供查詢、打卡、評論、用戶資訊、LINE Bot webhook 等 API
   - 所有資料皆以 Firestore 為主
3. **前端互動**：
   - 地圖前端透過 API 取得店家、打卡、用戶資料
   - 用戶可登入、打卡、評論、參與拉麵轉盤推薦
   - 意見回饋頁面直接寫入 Firestore
4. **LINE Bot**：
   - 用戶可透過 LINE 與 Bot 互動，查詢拉麵店、推播推薦、分析個人紀錄

---

## 開發與維護注意事項

- **Firebase 金鑰**：
  - 後端需設置 `FIREBASE_KEY_JSON` 環境變數，內容為 Firebase 服務帳戶金鑰 JSON
- **API 金鑰**：
  - 前端需設置 Google Maps API Key
  - 後端需設置 LINE Channel Access Token
- **資料同步**：
  - 新增店家請先用爬蟲產生 json，再匯入 Firestore
- **部署**：
  - 建議用 Render 或其他支援 Python/FastAPI 的雲端平台
  - 需設置環境變數（見 render.yaml 範例）
- **本地測試**：
  - 前端、後端可分開啟動，API 預設 port 10000
- **LINE Bot 測試**：
  - 需設置 webhook URL，建議用 ngrok 本地測試

---

## 交接建議

- 熟悉 Firebase 結構（users、ramen_shops、checkins、feedbacks）
- 熟悉 Google Maps API 與 LINE Bot SDK
- 爬蟲如需擴充，請參考 `find.py`、`find_many.py`
- 前端如需調整 UI/UX，請編輯 `frontend/ramen-map/src/`
- 後端如需擴充 API，請編輯 `line_bot_backend/`
- 有任何金鑰、API 變更，請同步更新前後端與雲端環境

---

## 聯絡窗口

- 專案原作者：
- 主要維護人：
- 相關帳號、API 金鑰、雲端平台存取權限請向管理員索取 