# 拉麵地圖系統（Ramen Map System）

---

## 1. 系統設計文件

### 1.1 目錄結構

```
├── frontend/                # 前端專案（地圖、意見回饋）
│   ├── ramen-map/           # 主地圖前端（純 JS + Google Maps）
│   └── feedback/            # 意見回饋頁面（Firebase 寫入）
├── line_bot_backend/        # FastAPI 後端 + LINE Bot + Firebase
├── Web Crawler/             # Google Maps 拉麵店爬蟲與資料處理
│   └── ramin/               # 爬蟲產生的 json、圖片等(已上傳到後端資料庫)
├── render.yaml              # Render 雲端部署設定
├── package.json             # 根目錄 JS 依賴（Google Maps 標記聚合）
└── ...
```

### 1.2 架構與資料流

- **資料來源**：Web Crawler 爬取 Google Maps，產生 json/圖片，匯入 Firebase Firestore/Storage
- **後端 API**：FastAPI 提供查詢、打卡、評論、用戶資訊、LINE Bot webhook 等 API，所有資料皆以 Firestore 為主
- **前端互動**：地圖前端透過 API 取得資料，用戶可登入、打卡、評論、參與拉麵轉盤推薦，意見回饋頁面直接寫入 Firestore
- **LINE Bot**：用戶可透過 LINE 與 Bot 互動，查詢拉麵店、推播推薦、分析個人紀錄

### 1.3 子系統功能與技術棧

#### 1.3.1 前端（frontend/ramen-map）
- 原生 JavaScript、HTML、CSS，Google Maps JavaScript API，Firebase
- 功能：地圖顯示、搜尋、打卡、評論、拉麵轉盤、個人紀錄

#### 1.3.2 意見回饋（frontend/feedback）
- 單頁 HTML + JS，Firebase Web SDK
- 功能：用戶意見回饋，直接寫入 Firestore

#### 1.3.3 後端 API 與 LINE Bot（line_bot_backend）
- Python 3.10+，FastAPI、Uvicorn、firebase-admin、line-bot-sdk
- 功能：API 服務、LINE Bot webhook、Firebase 整合

#### 1.3.4 爬蟲與資料處理（Web Crawler）
- Python、Selenium、webdriver-manager、pandas
- 功能：自動化爬取 Google Maps 拉麵店資訊，產生 json/圖片

### 1.4 Firebase Firestore 資料結構

```
集合：checkins/      # 打卡記錄
  ├── comment: string
  ├── keyword: string
  ├── photo_url: string
  ├── rating: number
  ├── store_id: string
  ├── store_name: string
  ├── timestamp: timestamp
  ├── user_id: string
  └── user_name: string

集合：feedbacks/     # 意見回饋
  ├── category: string
  ├── comment: string
  ├── timestamp: timestamp
  └── user_id: string

集合：ramen_shops/   # 店家主資料
  ├── address: string
  ├── keywords: array<string>
  ├── location: map (latitude, longitude)
  ├── menu_image: string
  ├── name: string
  ├── open_time: string
  ├── phone: string
  └── picture_image: string

集合：users/         # 使用者
  ├── display_name: string
  ├── joined_at: timestamp
  ├── last_updated: timestamp
  └── latlng: string
```

### 1.5 開發與維護注意事項

- **Firebase 金鑰**：後端需設置 `FIREBASE_KEY_JSON` 環境變數，內容為 Firebase 服務帳戶金鑰 JSON
- **API 金鑰**：前端需設置 Google Maps API Key，後端需設置 LINE Channel Access Token
- **資料同步**：新增店家請先用爬蟲產生 json，再匯入 Firestore
- **部署**：建議用 Render 或其他支援 Python/FastAPI 的雲端平台，需設置環境變數（見 render.yaml 範例）
- **本地測試**：前端、後端可分開啟動，API 預設 port 10000
- **LINE Bot 測試**：需設置 webhook URL，建議用 ngrok 本地測試
- **API 文件**：Swagger UI：[https://linebot-fastapi-uhmi.onrender.com/docs](https://linebot-fastapi-uhmi.onrender.com/docs)

---

## 2. 使用說明

### 2.1 啟動與部署

- **前端**：
  1. `cd frontend/ramen-map && npm install && npm start`
  2. 以 `serve .` 啟動本地伺服器
- **後端**：
  1. `cd line_bot_backend && pip install -r requirements.txt`
  2. `uvicorn main:app --reload --port 10000`
- **爬蟲**：
  1. 安裝 Chrome Driver
  2. `python find.py` 或 `python find_many.py`
- **意見回饋**：
  1. 開啟 `frontend/feedback/index.html` 於瀏覽器
- **部署**：
  1. 參考 `render.yaml`，設置環境變數並部署於 Render

### 2.2 交接與維護建議

- 熟悉 Firebase 結構（users、ramen_shops、checkins、feedbacks）
- 熟悉 Google Maps API 與 LINE Bot SDK
- 爬蟲如需擴充，請參考 `find.py`、`find_many.py`
- 前端如需調整 UI/UX，請編輯 `frontend/ramen-map/src/`
- 後端如需擴充 API，請編輯 `line_bot_backend/`
- 有任何金鑰、API 變更，請同步更新前後端與雲端環境

### 2.3 聯絡窗口

- 專案原作者：
- 主要維護人：
- 相關帳號、API 金鑰、雲端平台存取權限請向管理員索取

---

## 3. 測試報告

### 3.1 使用者故事地圖（User Story Map）

| 功能階段       | 進入拉 King 麵 | 瀏覽拉麵店家 | 選擇拉麵店家 / 品項 | 打卡互動     | 後續追蹤 / 分析與回饋             |
|----------------|----------------|----------------|----------------------|----------------|------------------------------------|
| **主流程**     | 進入拉 King 麵  | 搜尋拉麵店家    | 選擇拉麵品項           | 打卡紀錄       | 查看個人分析、意見回饋             |
|                | 透過 LINE 登入 | 檢視拉麵店家    |                      |                |                                    |
| **MVP 功能**   | LINE Bot 聊天室 | 偏好條件篩選    | 查看菜單               | 拉麵轉盤       | 上傳照片、每月統整、意見回饋       |
|                | LINE Bot 功能列 | 瀏覽拉麵地圖    | 查看評論區             | 給予評論       | 查看店家資訊                        |
| **進階功能**   | LINE 好友同步   | 好友打卡紀錄顯示 | 評論區條件篩選         | 個人化推薦     | 社群分享、個人喜好排行、新增店家   |
|                | 聊天功能（LLM） | 拉麵排行榜       | 加入口袋名單           | 成就與徽章     | 最新公告、資訊更新、黑名單管理     |

> 橫軸為使用者操作流程步驟，縱軸為功能開發層次（主流程 → MVP → 進階優化）。此表可作為功能追蹤、版本規劃與交付驗收依據。

### 3.2 使用者測試摘要

| 測試功能       | 測試任務簡述                                   | 完成率 | 發現問題 / 建議改進                        | 功能優化措施              |
|----------------|-----------------------------------------------|--------|--------------------------------------------|---------------------------|
| 拉麵地圖       | 搜尋並查看兩間拉麵店的地址與營業時間           | 100%   | 營業時間格式不一致、空值顯示為 Null        | 統一時間格式，空值顯示「尚無資料」 |
| 拉麵推薦       | 根據位置 + 偏好篩選 10 間豚骨拉麵店             | 80%    | 不清楚如何傳送定位；推薦功能未在地圖中發現 | 增加教學說明、入口統一   |
| 拉麵轉盤       | 加入 3 間店家進轉盤                              | 70%    | 加號按鈕不夠直覺，缺乏清空功能              | 改為「清空轉盤」按鈕     |
| 打卡上傳       | 完成一筆打卡並查詢個人紀錄                      | 100%   | 打卡紀錄圖示不明顯                          | Icon 加入文字標註        |
| 統整分析       | 提交 4 筆打卡並查看分析 Dump                    | 100%   | 平手情況下僅顯示一家                        | 改為平手多家一併顯示     |
| 意見回饋       | 選擇類型並填寫建議後送出                        | 100%   | 無                                          | UI 流程順暢，分類實用    |

#### 測試方式與亮點

- **使用者數量**：10 人
- **測試流程**：
  1. 測試前自由探索界面（介面初印象 + Bug 回饋）
  2. 測試中依序執行 6 項指定任務（任務導向測試）
  3. 測試後整體使用經驗訪談
- **資料蒐集方式**：觀察 + 訪談 + 功能迭代

- **亮點總結**：
  - 介面流程清晰、互動設計具吸引力
  - 打卡 + Dump 分析功能提升使用者參與度
  - 地圖資訊整合成功解決資訊分散問題
  - 拉麵轉盤深受有選擇障礙的使用者喜愛