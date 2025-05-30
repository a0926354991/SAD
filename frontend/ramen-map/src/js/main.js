import { GOOGLE_MAPS_MAP_ID } from './config.js';

let map;
let marker;
let nameLabel;
let currentStore = null;
let wheelStores = []; // 新增：儲存轉盤中的商店
let allStores = []; // 新增：儲存所有拉麵店資料
let allMarkers = []; // 新增：儲存所有標記

// 新增：登入相關變數
let currentUser = null;

// 新增：自定義事件系統
const storeEvents = {
    listeners: {},
    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    },
    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => callback(data));
        }
    }
};

// 新增：檢查登入狀態
async function checkLoginStatus() {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get("user_id");
    
    if (userId) {
        try {
            const response = await fetch(`https://linebot-fastapi-uhmi.onrender.com/users/${userId}`);
            const data = await response.json();
            
            if (data.status === "success") {
                currentUser = data.user; // 存儲完整的用戶資料
                updateLoginUI();
            } else {
                console.error('User not found:', data.message);
            }
        } catch (error) {
            console.error('Error checking login status:', error);
        }
    }
}

// 新增：添加用戶位置標記
function addUserLocationMarker(lat, lng) {
    // 移除舊的用戶位置標記（如果存在）
    if (window.userLocationMarker) {
        window.userLocationMarker.setMap(null);
    }

    // 創建新的標記
    const markerContent = document.createElement("div");
    markerContent.className = "marker-content user-location-marker";
    
    // 添加用戶位置圖標
    const userIcon = document.createElement("img");
    userIcon.src = "./src/assets/images/user-location.png";
    userIcon.className = "user-marker-img user-location-icon";
    markerContent.appendChild(userIcon);

    // 創建標記
    window.userLocationMarker = new google.maps.marker.AdvancedMarkerElement({
        map,
        position: { lat, lng },
        content: markerContent,
        title: "您的位置",
        zIndex: 1000  // 確保用戶位置標記在最上層
    });
}

// 新增：更新登入UI
function updateLoginUI() {
    const loginButton = document.getElementById('loginButton');
    const userInfo = document.getElementById('userInfo');
    
    if (currentUser) {
        loginButton.style.display = 'none';
        userInfo.style.display = 'flex';
        userInfo.querySelector('.username').textContent = currentUser.display_name;
    } else {
        loginButton.style.display = 'flex';
        userInfo.style.display = 'none';
    }
}

// 新增：顯示提示訊息
function showToast(message) {
    const toastContainer = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toast.style.zIndex = '9999'; // 確保顯示在最上層
    toastContainer.appendChild(toast);

    // 3秒後移除提示訊息
    setTimeout(() => {
        toast.remove();
    }, 1500);
}

// 新增：檢查店家是否在轉盤中
function isStoreInWheel(store) {
    return wheelStores.some(wheelStore => 
        wheelStore.name === store.name && 
        wheelStore.address === store.address
    );
}

// 新增：更新加入/移除按鈕的圖示
function updateAddToWheelButton(store) {
    const addToWheelFab = document.getElementById('addToWheelFab');
    if (store && isStoreInWheel(store)) {
        addToWheelFab.innerHTML = '<i class="fas fa-minus"></i>';
    } else {
        addToWheelFab.innerHTML = '<i class="fas fa-plus"></i>';
    }
}

// 新增：即時搜尋功能
function searchStores(query, showToast = false, selectFirst = false, isQuickCheckIn = false) {
    const searchResults = allStores.filter(store => 
        store.name.toLowerCase().includes(query.toLowerCase()) ||
        store.address.toLowerCase().includes(query.toLowerCase()) ||
        (store.keywords && store.keywords.some(keyword => 
            keyword.toLowerCase().includes(query.toLowerCase())
        ))
    );

    const searchResultsList = isQuickCheckIn ? 
        document.getElementById('quickCheckInResults') : 
        document.getElementById('searchResults');
    
    searchResultsList.innerHTML = '';

    if (query.trim() === '') {
        searchResultsList.style.display = 'none';
        return;
    }

    if (searchResults.length > 0) {
        searchResults.forEach((store, index) => {
            const resultItem = document.createElement('div');
            resultItem.className = 'search-result-item';
            resultItem.innerHTML = `
                <div class="store-name">${store.name}</div>
                <div class="store-address">${store.address}</div>
            `;
            resultItem.addEventListener('click', () => {
                if (isQuickCheckIn) {
                    selectStoreForQuickCheckIn(store);
                } else {
                    selectStore(store);
                }
                searchResultsList.style.display = 'none';
            });
            searchResultsList.appendChild(resultItem);

            // 如果是第一個結果且需要選中，則選中它
            if (index === 0 && selectFirst) {
                if (isQuickCheckIn) {
                    selectStoreForQuickCheckIn(store);
                } else {
                    selectStore(store);
                }
                searchResultsList.style.display = 'none';
            }
        });
        // 只有在即時搜尋時才顯示結果列表
        if (!selectFirst) {
            searchResultsList.style.display = 'block';
        }
    } else {
        searchResultsList.style.display = 'none';
        // 當需要顯示提示且沒有結果時，顯示提示訊息
        if (showToast) {
            showToast('😭找不到符合的店家😭');
        }
    }
}

// 新增：選擇店家
function selectStore(store) {
    const position = {
        lat: store.location.latitude,
        lng: store.location.longitude
    };
    
    const newCenter = {
        lat: position.lat - 0.0015,
        lng: position.lng
    };
    
    map.panTo(newCenter);
    map.setZoom(16);

    renderStoreInfo(store);
    showCheckInButton(store);

    // 找到對應的標記並只顯示它
    const selectedMarker = allMarkers.find(marker => marker.store === store);
    if (selectedMarker) {
        showOnlySelectedMarker(selectedMarker);
    }
}

// 新增：快速打卡相關的 DOM 元素
const quickCheckInModal = document.getElementById('quickCheckInModal');
const quickCheckInSearch = document.getElementById('quickCheckInSearch');
const quickCheckInResults = document.getElementById('quickCheckInResults');
const quickCheckInForm = document.getElementById('quickCheckInForm');
const quickCheckInStoreInfo = document.querySelector('#quickCheckInModal .store-info');
const quickCheckInStoreName = document.getElementById('quickCheckInStoreName');
const quickCheckInStoreAddress = document.getElementById('quickCheckInStoreAddress');
const quickCheckInRating = document.getElementById('quickCheckInRating');
const quickCheckInRatingStars = document.querySelectorAll('#quickCheckInModal .rating-input i');
const quickCheckInPhoto = document.getElementById('quickCheckInPhoto');
const quickCheckInPhotoPreview = document.getElementById('quickCheckInPhotoPreview');

// 新增：開啟快速打卡頁面
function openQuickCheckInModal() {
    if (!canCheckIn()) return;
    
    quickCheckInModal.classList.add('active');
    document.body.classList.add('modal-open');
    quickCheckInSearch.focus();
}

// 新增：關閉快速打卡頁面
function closeQuickCheckInModal() {
    quickCheckInModal.classList.remove('active');
    document.body.classList.remove('modal-open');
    quickCheckInForm.reset();
    quickCheckInPhotoPreview.innerHTML = '';
    quickCheckInRatingStars.forEach(star => star.classList.remove('active'));
    quickCheckInStoreInfo.style.display = 'none';
    quickCheckInResults.innerHTML = '';
    quickCheckInSearch.value = '';
}

// 新增：選擇店家進行快速打卡
function selectStoreForQuickCheckIn(store) {
    currentStore = store;
    quickCheckInStoreName.textContent = store.name;
    quickCheckInStoreAddress.textContent = store.address;
    quickCheckInStoreInfo.style.display = 'block';
    quickCheckInResults.innerHTML = '';
    quickCheckInSearch.value = store.name;

    // 更新關鍵字選擇區域
    const keywordContainer = document.getElementById('quickCheckInKeywordContainer');
    keywordContainer.innerHTML = '';
    
    if (store.keywords && store.keywords.length > 0) {
        store.keywords.forEach(keyword => {
            const keywordBtn = document.createElement('button');
            keywordBtn.type = 'button';
            keywordBtn.className = 'keyword-btn';
            keywordBtn.textContent = `#${keyword}`;
            keywordBtn.dataset.keyword = keyword;
            keywordBtn.addEventListener('click', () => {
                document.querySelectorAll('#quickCheckInModal .keyword-btn').forEach(btn => {
                    btn.classList.remove('selected');
                });
                keywordBtn.classList.add('selected');
                document.getElementById('quickCheckInSelectedKeyword').value = keyword;
                document.getElementById('quickCheckInOtherKeywordInput').style.display = 'none';
                document.getElementById('quickCheckInOtherKeywordInput').value = '';
            });
            keywordContainer.appendChild(keywordBtn);
        });
    }
    
    // 添加"其他"選項
    const otherBtn = document.createElement('button');
    otherBtn.type = 'button';
    otherBtn.className = 'keyword-btn';
    otherBtn.textContent = '#其他';
    otherBtn.dataset.keyword = 'other';
    otherBtn.addEventListener('click', () => {
        document.querySelectorAll('#quickCheckInModal .keyword-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        otherBtn.classList.add('selected');
        document.getElementById('quickCheckInOtherKeywordInput').style.display = 'block';
        document.getElementById('quickCheckInOtherKeywordInput').focus();
    });
    keywordContainer.appendChild(otherBtn);
    
    // 其他關鍵字輸入框
    const otherInput = document.createElement('input');
    otherInput.type = 'text';
    otherInput.id = 'quickCheckInOtherKeywordInput';
    otherInput.placeholder = '請輸入其他關鍵字';
    otherInput.style.display = 'none';
    otherInput.addEventListener('input', (e) => {
        document.getElementById('quickCheckInSelectedKeyword').value = e.target.value;
    });
    keywordContainer.appendChild(otherInput);
}

// 新增：處理快速打卡評分點擊
function handleQuickCheckInRatingClick(e) {
    const rating = parseInt(e.target.dataset.rating);
    quickCheckInRating.value = rating;
    
    const ratingError = document.querySelector('#quickCheckInModal .rating-error');
    ratingError.style.display = 'none';
    
    quickCheckInRatingStars.forEach(star => {
        const starRating = parseInt(star.dataset.rating);
        star.classList.toggle('active', starRating <= rating);
    });
}

// 新增：處理快速打卡照片預覽
function handleQuickCheckInPhotoPreview(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            quickCheckInPhotoPreview.innerHTML = `<img src="${e.target.result}" alt="預覽照片">`;
        };
        reader.readAsDataURL(file);
    }
}

// 新增：處理快速打卡提交
async function handleQuickCheckInSubmit(e) {
    e.preventDefault();
    
    // 驗證所有必填欄位
    const ratingValue = quickCheckInRating.value;
    const commentValue = document.getElementById('quickCheckInComment').value.trim();
    const photoFile = quickCheckInPhoto.files[0];
    const selectedKeyword = document.getElementById('quickCheckInSelectedKeyword').value;
    const otherKeywordInput = document.getElementById('quickCheckInOtherKeywordInput');
    
    let hasError = false;
    let finalKeyword = selectedKeyword;
    
    // 驗證店家選擇
    const storeError = document.createElement('div');
    storeError.className = 'field-error';
    storeError.style.display = 'none';
    storeError.style.color = '#ff6b6b';
    storeError.style.fontSize = '0.9em';
    storeError.style.marginTop = '5px';
    storeError.textContent = '請選擇一家拉麵店';
    
    const searchBox = document.querySelector('#quickCheckInModal .search-box');
    if (!searchBox.querySelector('.field-error')) {
        searchBox.appendChild(storeError);
    }
    
    if (!currentStore) {
        storeError.style.display = 'block';
        hasError = true;
    } else {
        storeError.style.display = 'none';
    }
    
    // 驗證評分
    const ratingError = document.querySelector('#quickCheckInModal .rating-error');
    if (!ratingValue) {
        ratingError.style.display = 'block';
        hasError = true;
    } else {
        ratingError.style.display = 'none';
    }
    
    // 驗證評論
    const commentError = document.querySelector('#quickCheckInComment').nextElementSibling;
    if (!commentValue) {
        commentError.style.display = 'block';
        hasError = true;
    } else {
        commentError.style.display = 'none';
    }
    
    // 驗證照片
    const photoError = document.querySelector('#quickCheckInPhoto').nextElementSibling.nextElementSibling;
    if (!photoFile) {
        photoError.style.display = 'block';
        hasError = true;
    } else {
        photoError.style.display = 'none';
    }
    
    // 驗證關鍵字
    const keywordError = document.querySelector('#quickCheckInModal .keyword-error');
    if (!selectedKeyword) {
        keywordError.style.display = 'block';
        hasError = true;
    } else if (selectedKeyword === 'other') {
        const customKeyword = otherKeywordInput.value.trim();
        if (!customKeyword) {
            keywordError.textContent = '請輸入其他關鍵字';
            keywordError.style.display = 'block';
            hasError = true;
        } else {
            finalKeyword = customKeyword;
            keywordError.style.display = 'none';
        }
    } else {
        keywordError.style.display = 'none';
    }
    
    if (hasError) {
        return;
    }

    // 防止重複提交
    const submitBtn = quickCheckInForm.querySelector('.submit-btn');
    if (submitBtn.disabled) {
        return;
    }
    
    // 設定 loading 狀態
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 提交中...';

    // 處理照片上傳
    let photoUrl = '';
    
    try {
        const formData = new FormData();
        formData.append('file', photoFile);
        
        const uploadResponse = await fetch('https://linebot-fastapi-uhmi.onrender.com/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            throw new Error('照片上傳失敗');
        }
        
        const uploadResult = await uploadResponse.json();
        photoUrl = uploadResult.url;
    } catch (error) {
        console.error('Error uploading photo:', error);
        showToast('照片上傳失敗，請稍後再試');
        submitBtn.disabled = false;
        submitBtn.textContent = '打卡';
        return;
    }

    const formData = {
        store_id: currentStore.name,
        user_id: currentUser.id,
        rating: parseFloat(ratingValue),
        comment: commentValue,
        photo_url: photoUrl,
        keyword: finalKeyword  // 使用最終確定的關鍵字
    };
    console.log('Submitting form data:', formData);

    try {
        const response = await fetch('https://linebot-fastapi-uhmi.onrender.com/checkin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        
        if (response.ok) {
            showToast('打卡成功！');
            closeQuickCheckInModal();
            // 重新載入打卡紀錄
            const checkinsList = document.querySelector('.checkins-list');
            if (checkinsList) {
                checkinsList.innerHTML = ''; // 清空現有記錄
                loadStoreCheckins(currentStore.id); // 重新載入
            }
        } else {
            const errorMessage = result.detail || '提交失敗';
            console.error('Error submitting form:', errorMessage);
            showToast(errorMessage);
        }
    } catch (error) {
        console.error('Error submitting form:', error.message || error);
        showToast('提交失敗，請稍後再試');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '打卡';
    }
}

// 修改：處理所有 URL 參數
function handleUrlParameters() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // 1. 處理登入狀態 - 移到 checkLoginStatus 函式中
    
    // 2. 處理轉盤店家列表
    const idsParam = urlParams.get("store_ids");
    if (idsParam) {
        storeEvents.on('storesLoaded', (stores) => {
            const ramenIds = idsParam.split(",");
            wheelStores = stores.filter(store => ramenIds.includes(String(store.id)));
            // 如果有 show_wheel 參數，在設置完 wheelStores 後立即繪製轉盤
            if (urlParams.get("show_wheel") === "1") {
                const wheelModal = document.getElementById('wheelModal');
                wheelModal.classList.add('active');
                document.body.classList.add('modal-open');
                window.drawWheel();
            }
        });
    } 
    
    // 3. 處理是否顯示轉盤 - 移到 store_ids 處理中
    
    // 4. 處理自動聚焦單一店家
    const storeId = urlParams.get("store_id");
    if (storeId && typeof selectStore === "function") {
        storeEvents.on('storesLoaded', (stores) => {
            // 先嘗試用 id 比對
            let store = stores.find(s => String(s.id) === String(storeId));
            
            // 如果找不到，再嘗試用 name 比對
            if (!store) {
                store = stores.find(s => s.name === storeId);
            }
            
            console.log('Found store:', store);
            
            if (store) {
                selectStore(store);
            } else {
                console.error('Store not found with id/name:', storeId);
            }
        });
    }

    // 5. 處理快速打卡
    if (urlParams.get("quick_checkin") === "1") {
        storeEvents.on('storesLoaded', () => {
            initQuickCheckIn();
            openQuickCheckInModal();
        });
    }
}

// Initialize the map
async function initMap() {
    // Center on Taipei
    const taipei = { lat: 25.0330, lng: 121.5654 };
    //@ts-ignore
    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    map = new Map(document.getElementById("map"), {
        zoom: 13,
        center: taipei,
        mapId: GOOGLE_MAPS_MAP_ID,
        disableDefaultUI: true
        
    });

    // 如果有用戶位置，設置地圖中心和標記
    if (currentUser && currentUser.latlng) {
        
        const { latitude, longitude } = currentUser.latlng;
        map.setCenter({ lat: latitude, lng: longitude });
        map.setZoom(17);
        addUserLocationMarker(latitude, longitude);
    }

    // 讀取拉麵店資料
    fetch("https://linebot-fastapi-uhmi.onrender.com/all_shops")
        .then(response => response.json())
        .then(data => {
            allStores = data.ramen_stores;
            
            // 觸發 stores 載入完成事件
            storeEvents.emit('storesLoaded', allStores);

            data.ramen_stores.forEach(store => {
                const position = {
                    lat: store.location.latitude,
                    lng: store.location.longitude
                };

                // marker 內容只放圖片
                const markerContent = document.createElement("div");
                markerContent.className = "marker-content";

                // 圖片
                const ramenImg = document.createElement("img");
                ramenImg.src = "./src/assets/images/ramen-marker.jpg";
                ramenImg.className = "ramen-marker-img";

                markerContent.appendChild(ramenImg);

                const nameDiv = document.createElement("div");
                nameDiv.textContent = store.name;
                nameDiv.className = "marker-store-name";
                markerContent.appendChild(nameDiv);

                // 建立 marker
                const marker = new AdvancedMarkerElement({
                    map,
                    position,
                    content: markerContent,
                    title: store.name,
                    gmpClickable: true
                });

                // 儲存標記和店家的關聯
                marker.store = store;
                allMarkers.push(marker);

                // 點擊 marker 時顯示店名和打卡按鈕
                marker.addListener("gmp-click", () => {
                    renderStoreInfo(store);
                    panMapToSafeBounds(map, position);
                    showCheckInButton(store);
                });

                // 點擊地圖其他地方時隱藏店名和打卡按鈕
                map.addListener("click", () => {
                    showDefaultPage();
                    hideCheckInButton();
                    showAllMarkers();
                });
            });
        })
        .catch(error => console.error('Error loading ramen data:', error));
}

// 底部面板滾動控制
const ramenList = document.getElementById('ramenList');
const ramenListHandle = document.querySelector('.ramen-list-handle');
let lastScrollTop = 0;
let isScrolling = false;
let scrollTimeout;

// 點擊手柄切換面板狀態
ramenListHandle.addEventListener('click', () => {
    ramenList.classList.toggle('active');
    if (ramenList.classList.contains('active')) {
        ramenList.style.transform = 'translateY(0)';
    } else {
        ramenList.style.transform = 'translateY(calc(100% - 50px))';
    }
});

// 監聽面板滾動
ramenList.addEventListener('scroll', () => {
    if (!isScrolling) {
        isScrolling = true;
        clearTimeout(scrollTimeout);
    }

    const currentScroll = ramenList.scrollTop;
    const scrollDirection = currentScroll > lastScrollTop ? 'down' : 'up';

    if (scrollDirection === 'down') {
        ramenList.classList.add('active');
        ramenList.style.transform = 'translateY(0)';
        ramenList.style.maxHeight = '80vh';
    }

    lastScrollTop = currentScroll;

    scrollTimeout = setTimeout(() => {
        isScrolling = false;
    }, 150);
});

// 將詳細資訊渲染到右側欄
function renderStoreInfo(store) {
    const ramenItems = document.getElementById('ramenItems');
    
    // 創建標籤頁容器
    ramenItems.innerHTML = `
        <div class="store-info-full">
            <div class="tabs">
                <button class="tab-btn active" data-tab="info">店家資訊</button>
                <button class="tab-btn" data-tab="checkins">打卡紀錄</button>
            </div>
            
            <div class="tab-content">
                <div class="tab-pane active" id="info-tab">
                    <div class="store-header">
                        <div class="store-title">${store.name}</div>
                        <div class="store-address"><i class='fas fa-map-marker-alt'></i> ${store.address || ''}</div>
                    </div>
                    <div class="store-section">
                        <div class="store-label">評分</div>
                        <div class="store-value"><i class="fas fa-star" style="color: #F1C40F;"></i> ${store.rating}</div>
                    </div>
                    <div class="store-section">
                        <div class="store-label">關鍵字</div>
                        <div class="store-value">
                            ${store.keywords ? store.keywords.map(kw => `<b>#${kw}</b>`).join(' ') : ''}
                        </div>
                    </div>
                    <div class="store-section">
                        <div class="store-label">營業時間</div>
                        <div class="store-value">${store.open_time ? store.open_time.replace(/; ?/g, '<br>') : '無資料'}</div>
                    </div>
                    <div class="store-menu-img">
                        <div class="menu-title">菜單</div>
                        <img src="${store.menu_image || ''}" alt="${store.name} 菜單" style="width:100%;max-width:350px;margin:10px auto 0;display:block;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);background:#fafafa;" />
                    </div>
                </div>
                
                <div class="tab-pane" id="checkins-tab">
                    <div class="checkins-container">
                        <div class="checkins-list"></div>
                        <button class="load-more-btn" style="display: none;">顯示更多</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // 初始化打卡紀錄
    loadStoreCheckins(store.id);

    // 綁定標籤頁切換事件
    const tabBtns = ramenItems.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const tabPanes = ramenItems.querySelectorAll('.tab-pane');
            tabPanes.forEach(pane => pane.classList.remove('active'));
            ramenItems.querySelector(`#${btn.dataset.tab}-tab`).classList.add('active');
        });
    });

    ramenList.classList.add('active');
    ramenList.style.transform = 'translateY(0)';
    ramenList.style.maxHeight = 'var(--panel-height)';
}

// 新增：載入店家打卡紀錄
async function loadStoreCheckins(storeId, lastId = null) {
    try {
        const url = `https://linebot-fastapi-uhmi.onrender.com/store_checkins/${storeId}?limit=5` + (lastId ? `&last_id=${lastId}` : '');
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.status === "success") {
            const checkinsList = document.querySelector('.checkins-list');
            const loadMoreBtn = document.querySelector('.load-more-btn');
            
            // 如果是第一次載入且沒有打卡記錄
            if (!lastId && data.checkins.length === 0) {
                checkinsList.innerHTML = `
                    <div class="no-checkins-message">
                        <i class="fas fa-utensils"></i>
                        <p>還沒有任何打卡記錄</p>
                        <p class="sub-text">來當第一個打卡的人吧！</p>
                    </div>
                `;
                loadMoreBtn.style.display = 'none';
                return;
            }
            
            // 渲染打卡紀錄
            data.checkins.forEach(checkin => {
                const checkinElement = createCheckinElement(checkin);
                checkinsList.appendChild(checkinElement);
            });
            
            // 控制"顯示更多"按鈕和到底提示
            if (data.has_more) {
                loadMoreBtn.style.display = 'block';
                loadMoreBtn.onclick = () => {
                    const lastCheckin = data.checkins[data.checkins.length - 1];
                    loadStoreCheckins(storeId, lastCheckin.id);
                };
            } else {
                const endMessage = document.createElement('div');
                endMessage.className = 'end-message';
                endMessage.innerHTML = `
                    <i class="fas fa-flag-checkered"></i>
                    <p>已經到底了！</p>
                `;
                checkinsList.appendChild(endMessage);
                loadMoreBtn.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error loading checkins:', error);
        showToast('載入打卡紀錄失敗');
    }
}

// 新增：創建打卡紀錄元素
function createCheckinElement(checkin) {
    const div = document.createElement('div');
    div.className = 'checkin-item';
    div.innerHTML = `
        <div class="checkin-header">
            <div class="checkin-user">${checkin.user_name}</div>
            <div class="checkin-time">${formatDate(checkin.timestamp)}</div>
        </div>
        <div class="checkin-content">
            <div class="checkin-keyword">#${checkin.keyword || '其他'}</div>
            <div class="checkin-rating">
                <div class="stars">${'★'.repeat(Math.round(checkin.rating))}${'☆'.repeat(5 - Math.round(checkin.rating))}</div>
                <div class="rating-value">${checkin.rating}</div>
            </div>
            <div class="checkin-comment">${checkin.comment}</div>
            ${checkin.photo_url ? `
                <div class="checkin-photo">
                    <img src="${checkin.photo_url}" alt="打卡照片" />
                </div>
            ` : ''}
        </div>
    `;
    return div;
}

// 新增：格式化日期
function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 點擊地圖空白處時，恢復預設狀態
function showDefaultPage() {
    const ramenItems = document.getElementById('ramenItems');
    if (ramenItems) ramenItems.innerHTML = '';

    ramenList.classList.remove('active');
    ramenList.style.transform = 'translateY(calc(100% - 50px))';
    ramenList.style.maxHeight = 'var(--panel-height)';

    // 顯示所有標記
    showAllMarkers();
}

// 檢查並移動地圖，確保標記在安全範圍內
function panMapToSafeBounds(map, position) {
    const bounds = map.getBounds();
    if (!bounds) return;

    const ne = bounds.getNorthEast();
    const sw = bounds.getSouthWest();
    const latPadding = (ne.lat() - sw.lat()) * 0.2;
    const lngPadding = (ne.lng() - sw.lng()) * 0.2;

    const safeBounds = {
        north: ne.lat() - latPadding,
        south: sw.lat() + latPadding,
        east: ne.lng() - lngPadding,
        west: sw.lng() + lngPadding
    };

    if (position.lat > safeBounds.north || 
        position.lat < safeBounds.south || 
        position.lng > safeBounds.east || 
        position.lng < safeBounds.west) {
        const newCenter = {
            lat: position.lat > safeBounds.north ? safeBounds.north - latPadding * 0.5 :
                 position.lat < safeBounds.south ? safeBounds.south + latPadding * 0.5 :
                 map.getCenter().lat(),
            lng: position.lng > safeBounds.east ? safeBounds.east - lngPadding * 0.5 :
                 position.lng < safeBounds.west ? safeBounds.west + lngPadding * 0.5 :
                 map.getCenter().lng()
        };
        map.panTo(newCenter);
    }
}

// 打卡功能相關的 DOM 元素
const checkInFab = document.getElementById('checkInFab');
const checkInModal = document.getElementById('checkInModal');
const closeModal = document.querySelector('.close-modal');
const checkInForm = document.getElementById('checkInForm');
const storeNameElement = document.getElementById('checkInStoreName');
const storeAddressElement = document.getElementById('checkInStoreAddress');
const ratingInput = document.getElementById('storeRating');
const ratingStars = document.querySelectorAll('.rating-input i');
const photoInput = document.getElementById('checkInPhoto');
const photoPreview = document.getElementById('photoPreview');

// 開啟打卡頁面
function openCheckInModal(store) {
    currentStore = store;
    storeNameElement.textContent = store.name;
    storeAddressElement.textContent = store.address;
    
    // 新增：更新關鍵字選擇區域
    const keywordContainer = document.getElementById('keywordContainer');
    keywordContainer.innerHTML = ''; // 清空現有關鍵字
    
    if (store.keywords && store.keywords.length > 0) {
        store.keywords.forEach(keyword => {
            const keywordBtn = document.createElement('button');
            keywordBtn.type = 'button';
            keywordBtn.className = 'keyword-btn';
            keywordBtn.textContent = `#${keyword}`;
            keywordBtn.dataset.keyword = keyword;
            keywordBtn.addEventListener('click', () => {
                // 移除其他按鈕的選中狀態
                document.querySelectorAll('.keyword-btn').forEach(btn => {
                    btn.classList.remove('selected');
                });
                // 選中當前按鈕
                keywordBtn.classList.add('selected');
                // 更新隱藏的輸入欄位
                document.getElementById('selectedKeyword').value = keyword;
                // 隱藏其他關鍵字輸入框
                document.getElementById('otherKeywordInput').style.display = 'none';
                document.getElementById('otherKeywordInput').value = '';
            });
            keywordContainer.appendChild(keywordBtn);
        });
    }
    
    // 新增：添加"其他"選項
    const otherBtn = document.createElement('button');
    otherBtn.type = 'button';
    otherBtn.className = 'keyword-btn';
    otherBtn.textContent = '#其他';
    otherBtn.dataset.keyword = 'other';
    otherBtn.addEventListener('click', () => {
        // 移除其他按鈕的選中狀態
        document.querySelectorAll('.keyword-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        // 選中當前按鈕
        otherBtn.classList.add('selected');
        // 顯示其他關鍵字輸入框
        document.getElementById('otherKeywordInput').style.display = 'block';
        document.getElementById('otherKeywordInput').focus();
    });
    keywordContainer.appendChild(otherBtn);
    
    // 新增：其他關鍵字輸入框
    const otherInput = document.createElement('input');
    otherInput.type = 'text';
    otherInput.id = 'otherKeywordInput';
    otherInput.placeholder = '請輸入其他關鍵字';
    otherInput.style.display = 'none';
    otherInput.addEventListener('input', (e) => {
        document.getElementById('selectedKeyword').value = e.target.value;
    });
    keywordContainer.appendChild(otherInput);
    
    checkInModal.classList.add('active');
    document.body.classList.add('modal-open');
}

// 關閉打卡頁面
function closeCheckInModal() {
    checkInModal.classList.remove('active');
    document.body.classList.remove('modal-open');
    checkInForm.reset();
    photoPreview.innerHTML = '';
    ratingStars.forEach(star => star.classList.remove('active'));
}

// 處理評分星星點擊
function handleRatingClick(e) {
    const rating = parseInt(e.target.dataset.rating);
    ratingInput.value = rating;
    
    // 隱藏錯誤訊息
    const ratingError = document.querySelector('.rating-error');
    ratingError.style.display = 'none';
    
    ratingStars.forEach(star => {
        const starRating = parseInt(star.dataset.rating);
        star.classList.toggle('active', starRating <= rating);
    });
}

// 處理照片預覽
function handlePhotoPreview(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            photoPreview.innerHTML = `<img src="${e.target.result}" alt="預覽照片">`;
        };
        reader.readAsDataURL(file);
    }
}

// 顯示打卡按鈕
function showCheckInButton(store) {
    currentStore = store;
    checkInFab.classList.add('active');
    addToWheelFab.classList.add('active');
    updateAddToWheelButton(store); // 新增：更新按鈕圖示
}

// 隱藏打卡按鈕
function hideCheckInButton() {
    currentStore = null;
    checkInFab.classList.remove('active');
    addToWheelFab.classList.remove('active');
}

// 新增：檢查是否可以打卡
function canCheckIn() {
    if (!currentUser) {
        showToast('請先至LINEBOT登入！');
        return false;
    }
    return true;
}

// 新增：獲取附近的拉麵店
async function getNearbyShops(lat, lng, limit = 6) {
    try {
        const response = await fetch(`https://linebot-fastapi-uhmi.onrender.com/nearby_shops?lat=${lat}&lng=${lng}&limit=${limit}`);
        const data = await response.json();
        if (data.status === "success") {
            return data.shops;
        }
        return [];
    } catch (error) {
        console.error('Error getting nearby shops:', error);
        return [];
    }
}

// 新增：隨機選擇拉麵店
function getRandomShops(limit = 6) {
    const shuffled = [...allStores].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, limit);
}

// 拉麵轉盤功能
async function initWheel() {
    const wheelFab = document.getElementById('wheelFab');
    const wheelModal = document.getElementById('wheelModal');
    const closeWheelModal = document.getElementById('closeWheelModal');
    const spinButton = document.getElementById('spinButton');
    const confirmButton = document.getElementById('confirmButton');
    const canvas = document.getElementById('wheelCanvas');
    const selectedStoreName = document.getElementById('selectedStoreName');
    const ctx = canvas.getContext('2d');
    const addToWheelFab = document.getElementById('addToWheelFab');

    canvas.width = 300;
    canvas.height = 300;

    let currentRotation = 0;
    let isSpinning = false;
    let selectedStore = null;

    // 新增：初始化時加入附近的拉麵店
    if (currentUser && currentUser.latlng) {
        const { latitude, longitude } = currentUser.latlng;
        const nearbyShops = await getNearbyShops(latitude, longitude);
        if (nearbyShops.length > 0) {
            wheelStores = nearbyShops;
        } else {
            wheelStores = getRandomShops();
        }
    } else {
        wheelStores = getRandomShops();
    }

    // 修改：加入/移除轉盤的功能
    addToWheelFab.addEventListener('click', () => {
        if (currentStore) {
            const isInWheel = isStoreInWheel(currentStore);
            
            if (!isInWheel) {
                wheelStores.push(currentStore);
                showToast('🎉已將店家加入轉盤🎉');
            } else {
                // 從轉盤中移除店家
                wheelStores = wheelStores.filter(store => 
                    !(store.name === currentStore.name && 
                      store.address === currentStore.address)
                );
                showToast('🗑️已從轉盤移除店家🗑️');
            }
            
            // 更新按鈕圖示
            updateAddToWheelButton(currentStore);
            
            // 如果轉盤視窗是開啟的，重新繪製轉盤
            if (wheelModal.classList.contains('active')) {
                drawWheel();
            }
        }
    });

    // 將 drawWheel 函數設為全局可訪問
    window.drawWheel = function() {
        console.log('drawWheel called, wheelStores:', wheelStores);
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 10;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (wheelStores.length === 0) {
            console.log('wheelStores is empty in drawWheel');
            // 如果轉盤為空，顯示提示文字
            ctx.fillStyle = '#f8f9fa';
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
            ctx.fill();
            
            ctx.fillStyle = '#666';
            ctx.font = '16px Noto Sans JP';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('請先加入店家', centerX, centerY);
            return;
        }
        
        const anglePerSlice = (2 * Math.PI) / wheelStores.length;
        
        wheelStores.forEach((store, index) => {
            const startAngle = index * anglePerSlice + currentRotation;
            const endAngle = (index + 1) * anglePerSlice + currentRotation;
            
            const colors = ['#E87A90', '#88C9A1', '#F7B977'];
            let colorIndex;
            if (index === wheelStores.length - 1) {
                const prevColor = (index - 1) % 3;
                const firstColor = 0;
                colorIndex = colors.findIndex((_, i) => i !== prevColor && i !== firstColor);
            } else {
                colorIndex = index % 3;
            }
            ctx.fillStyle = colors[colorIndex];
            
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, startAngle, endAngle);
            ctx.closePath();
            ctx.fill();
            
            ctx.save();
            ctx.translate(centerX, centerY);
            ctx.rotate(startAngle + anglePerSlice / 2);
            ctx.textAlign = 'right';
            ctx.fillStyle = 'white';
            ctx.font = '14px Noto Sans JP';
            ctx.fillText(store.name, radius - 20, 5);
            ctx.restore();
        });
        
        ctx.beginPath();
        ctx.arc(centerX, centerY, 10, 0, 2 * Math.PI);
        ctx.fillStyle = '#2C3E50';
        ctx.fill();
        
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - radius);
        ctx.lineTo(centerX - 10, centerY - radius + 20);
        ctx.lineTo(centerX + 10, centerY - radius + 20);
        ctx.closePath();
        ctx.fillStyle = '#2C3E50';
        ctx.fill();
    };

    // 將 spinWheel 函數設為全局可訪問
    window.spinWheel = function() {
        if (isSpinning || wheelStores.length === 0) return;
        
        isSpinning = true;
        spinButton.disabled = true;
        confirmButton.disabled = true;
        selectedStoreName.textContent = '轉動中...';
        
        const spinAngle = (Math.random() * 5 + 5) * 2 * Math.PI;
        const duration = 3000;
        const startTime = performance.now();
        
        function animate(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const easeProgress = 1 - (1 - progress) * (1 - progress);
            
            currentRotation = spinAngle * easeProgress;
            drawWheel();
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                isSpinning = false;
                spinButton.disabled = false;
                confirmButton.disabled = false;
                
                const anglePerSlice = (2 * Math.PI) / wheelStores.length;
                const pointerAngle = -Math.PI / 2;
                let idx = ((pointerAngle - currentRotation) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) / anglePerSlice;
                const selectedIndex = Math.floor(idx);
                selectedStore = wheelStores[selectedIndex];
                selectedStoreName.textContent = selectedStore.name;
            }
        }
        
        requestAnimationFrame(animate);
    };

    wheelFab.addEventListener('click', () => {
        console.log('wheelFab clicked, wheelStores:', wheelStores);
        wheelModal.classList.add('active');
        document.body.classList.add('modal-open');
        drawWheel();
    });

    canvas.addEventListener('click', () => {
        if (!isSpinning && wheelStores.length > 0) {
            spinWheel();
        }
    });

    closeWheelModal.addEventListener('click', () => {
        wheelModal.classList.remove('active');
        document.body.classList.remove('modal-open');
    });

    spinButton.addEventListener('click', spinWheel);

    confirmButton.addEventListener('click', () => {
        if (selectedStore) {
            selectStore(selectedStore);
            wheelModal.classList.remove('active');
            document.body.classList.remove('modal-open');
        }
    });

    wheelModal.addEventListener('click', (e) => {
        if (e.target === wheelModal) {
            wheelModal.classList.remove('active');
            document.body.classList.remove('modal-open');
        }
    });
}

// 新增：只顯示選中的標記
function showOnlySelectedMarker(selectedMarker) {
    allMarkers.forEach(marker => {
        if (marker === selectedMarker) {
            marker.map = map;
        } else {
            marker.map = null;
        }
    });
}

// 新增：顯示所有標記
function showAllMarkers() {
    allMarkers.forEach(marker => {
        marker.map = map;
    });
}

// 新增：控制 loading 遮罩
function showLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}

function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

async function loadLiffScript() {
    return new Promise((resolve, reject) => {
        if (window.liff) return resolve();
        const script = document.createElement("script");
        script.src = "https://static.line-scdn.net/liff/edge/2/sdk.js";
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

async function ensureUserIdParam() {
    // 檢查 user_id，不要直接用 search，還要支援 hash
    let urlParams = new URLSearchParams(window.location.search);

    // 如果 search 沒參數、但 hash 有，就把 hash 拆成 query string
    if (!window.location.search && window.location.hash) {
        // 把 hash 開頭的 # 拿掉
        const hashString = window.location.hash.substring(1);
        urlParams = new URLSearchParams(hashString);
        // 直接轉換成 ? 參數再 reload
        window.location.search = '?' + hashString;
        return;
    }

    // 以下維持你的 user_id 判斷流程
    if (!urlParams.has("user_id")) {
        await loadLiffScript();
        await liff.init({ liffId: "2007489792-4popYn8a" });
        if (!liff.isInClient()) {
            showToast("請從LINE圖文選單打開本頁！");
            return;
        }
        const profile = await liff.getProfile();
        const userId = profile.userId;

        urlParams.set('user_id', userId);
        const searchString = urlParams.toString();
        window.location.href = `https://frontend-7ivv.onrender.com/ramen-map/?${searchString}`;
    }
}

// 新增：回到用戶位置
function centerOnUserLocation() {
    if (currentUser && currentUser.latlng) {
        const { latitude, longitude } = currentUser.latlng;
        map.setCenter({ lat: latitude, lng: longitude });
        map.setZoom(17);
    } else {
        showToast('無法獲取您的位置');
    }
}

// 新增：處理打卡提交
async function handleCheckInSubmit(e) {
    e.preventDefault();
    
    if (!currentStore) {
        alert('請先選擇一家拉麵店');
        return;
    }

    // 驗證所有必填欄位
    const ratingValue = ratingInput.value;
    const commentValue = document.getElementById('storeComment').value.trim();
    const photoFile = photoInput.files[0];
    const selectedKeyword = document.getElementById('selectedKeyword').value;
    const otherKeywordInput = document.getElementById('otherKeywordInput');
    
    let hasError = false;
    let finalKeyword = selectedKeyword;
    
    // 驗證評分
    const ratingError = document.querySelector('.rating-error');
    if (!ratingValue) {
        ratingError.style.display = 'block';
        hasError = true;
    } else {
        ratingError.style.display = 'none';
    }
    
    // 驗證評論
    const commentError = document.querySelector('#storeComment').nextElementSibling;
    if (!commentValue) {
        commentError.style.display = 'block';
        hasError = true;
    } else {
        commentError.style.display = 'none';
    }
    
    // 驗證照片
    const photoError = document.querySelector('#checkInPhoto').nextElementSibling.nextElementSibling;
    if (!photoFile) {
        photoError.style.display = 'block';
        hasError = true;
    } else {
        photoError.style.display = 'none';
    }
    
    // 驗證關鍵字
    const keywordError = document.querySelector('.keyword-error');
    if (!selectedKeyword) {
        keywordError.style.display = 'block';
        hasError = true;
    } else if (selectedKeyword === 'other') {
        const customKeyword = otherKeywordInput.value.trim();
        if (!customKeyword) {
            keywordError.textContent = '請輸入其他關鍵字';
            keywordError.style.display = 'block';
            hasError = true;
        } else {
            finalKeyword = customKeyword;
            keywordError.style.display = 'none';
        }
    } else {
        keywordError.style.display = 'none';
    }

    if (hasError) {
        return;
    }

    // 防止重複提交
    const submitBtn = checkInForm.querySelector('.submit-btn');
    if (submitBtn.disabled) {
        return;
    }
    
    // 設定 loading 狀態
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 提交中...';

    // 處理照片上傳
    let photoUrl = '';
    
    try {
        // 建立 FormData 物件
        const formData = new FormData();
        formData.append('file', photoFile);
        
        // 上傳照片到後端
        const uploadResponse = await fetch('https://linebot-fastapi-uhmi.onrender.com/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            throw new Error('照片上傳失敗');
        }
        
        const uploadResult = await uploadResponse.json();
        photoUrl = uploadResult.url;
    } catch (error) {
        console.error('Error uploading photo:', error);
        showToast('照片上傳失敗，請稍後再試');
        // 重置按鈕狀態
        submitBtn.disabled = false;
        submitBtn.textContent = '打卡';
        return;
    }

    const formData = {
        store_id: currentStore.name,
        user_id: currentUser.id,
        rating: parseFloat(ratingValue),
        comment: commentValue,
        photo_url: photoUrl,
        keyword: finalKeyword  // 使用最終確定的關鍵字
    };
    console.log('Submitting form data:', formData);

    try {
        const response = await fetch('https://linebot-fastapi-uhmi.onrender.com/checkin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();
        
        if (response.ok) {
            showToast('打卡成功！');
            closeCheckInModal();
            // 重新載入打卡紀錄
            const checkinsList = document.querySelector('.checkins-list');
            if (checkinsList) {
                checkinsList.innerHTML = ''; // 清空現有記錄
                loadStoreCheckins(currentStore.id); // 重新載入
            }
        } else {
            const errorMessage = result.detail || '提交失敗';
            console.error('Error submitting form:', errorMessage);
            showToast(errorMessage);
        }
    } catch (error) {
        console.error('Error submitting form:', error.message || error);
        showToast('提交失敗，請稍後再試');
    } finally {
        // 重置按鈕狀態
        submitBtn.disabled = false;
        submitBtn.textContent = '打卡';
    }
}

// 新增：初始化快速打卡功能
function initQuickCheckIn() {
    const quickCheckInModal = document.getElementById('quickCheckInModal');
    const quickCheckInSearch = document.getElementById('quickCheckInSearch');
    const quickCheckInResults = document.getElementById('quickCheckInResults');
    const quickCheckInForm = document.getElementById('quickCheckInForm');
    const quickCheckInStoreInfo = document.querySelector('#quickCheckInModal .store-info');
    const quickCheckInStoreName = document.getElementById('quickCheckInStoreName');
    const quickCheckInStoreAddress = document.getElementById('quickCheckInStoreAddress');
    const quickCheckInRating = document.getElementById('quickCheckInRating');
    const quickCheckInRatingStars = document.querySelectorAll('#quickCheckInModal .rating-input i');
    const quickCheckInPhoto = document.getElementById('quickCheckInPhoto');
    const quickCheckInPhotoPreview = document.getElementById('quickCheckInPhotoPreview');

    // 快速打卡功能事件監聽
    const quickCheckInCloseModal = document.querySelector('#quickCheckInModal .close-modal');
    
    quickCheckInCloseModal.addEventListener('click', closeQuickCheckInModal);

    quickCheckInModal.addEventListener('click', (e) => {
        if (e.target === quickCheckInModal) {
            closeQuickCheckInModal();
        }
    });

    // 修改：執行快速打卡搜尋的函數
    const performQuickCheckInSearch = () => {
        searchStores(quickCheckInSearch.value, true, true, true);
    };

    // 按下 Enter 時搜尋
    quickCheckInSearch.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performQuickCheckInSearch();
        }
    });

    // 即時搜尋，不顯示找不到的提示，不選中第一個
    quickCheckInSearch.addEventListener('input', (e) => {
        searchStores(e.target.value, false, false, true);
        if (e.target.value.trim() !== '') {
            quickCheckInResults.classList.add('active');
        } else {
            quickCheckInResults.classList.remove('active');
        }
    });

    quickCheckInRatingStars.forEach(star => {
        star.addEventListener('click', handleQuickCheckInRatingClick);
    });

    quickCheckInPhoto.addEventListener('change', handleQuickCheckInPhotoPreview);

    quickCheckInForm.addEventListener('submit', handleQuickCheckInSubmit);
}

// 修改：初始化所有功能
async function init() {
    showLoading();
    
    try {
        // 1. 確保有 user_id
        await ensureUserIdParam();

        await checkLoginStatus();

        // 2. 初始化地圖並獲取所有拉麵店資料
        await initMap();

        // 3. 檢查登入狀態並獲取用戶資料
        

        // 4. 初始化轉盤（需要 allStores 和 currentUser 數據）
        await initWheel();

        // 5. 新增：回到用戶位置按鈕
        const backToUserBtn = document.createElement('button');
        backToUserBtn.className = 'back-to-user-btn';
        backToUserBtn.innerHTML = '<i class="fas fa-crosshairs"></i>';
        backToUserBtn.title = '回到我的位置';
        backToUserBtn.addEventListener('click', centerOnUserLocation);
        document.querySelector('.main-content').appendChild(backToUserBtn);

        // 6. 初始化搜尋功能
        const searchInput = document.getElementById('searchInput');
        const searchBox = document.querySelector('.search-box');
        const searchToggle = document.querySelector('.search-toggle');
        const searchResults = document.getElementById('searchResults');

        // 切換搜尋欄顯示
        searchToggle.addEventListener('click', () => {
            searchBox.classList.toggle('active');
            if (searchBox.classList.contains('active')) {
                searchInput.focus();
            }
        });

        // 點擊其他地方時隱藏搜尋欄
        document.addEventListener('click', (e) => {
            if (!searchBox.contains(e.target) && !searchToggle.contains(e.target)) {
                searchBox.classList.remove('active');
                searchResults.classList.remove('active');
            }
        });

        // 執行搜尋的函數
        const performSearch = () => {
            searchStores(searchInput.value, true, true);
        };

        // 按下 Enter 時搜尋
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });

        // 即時搜尋，不顯示找不到的提示，不選中第一個
        searchInput.addEventListener('input', (e) => {
            searchStores(e.target.value, false, false);
            if (e.target.value.trim() !== '') {
                searchResults.classList.add('active');
            } else {
                searchResults.classList.remove('active');
            }
        });

        // 7. 初始化打卡功能
        initCheckIn();


        // 9. 處理所有 URL 參數
        handleUrlParameters();

    } catch (error) {
        console.error('Error during initialization:', error);
        showToast('載入失敗，請重新整理頁面');
    } finally {
        // 確保所有初始化完成後才隱藏 loading
        setTimeout(hideLoading, 500); // 添加小延遲以確保平滑過渡
    }
}

// 新增：初始化打卡功能
function initCheckIn() {
    const checkInFab = document.getElementById('checkInFab');
    const checkInModal = document.getElementById('checkInModal');
    const closeModal = document.querySelector('.close-modal');
    const checkInForm = document.getElementById('checkInForm');
    const storeNameElement = document.getElementById('checkInStoreName');
    const storeAddressElement = document.getElementById('checkInStoreAddress');
    const ratingInput = document.getElementById('storeRating');
    const ratingStars = document.querySelectorAll('.rating-input i');
    const photoInput = document.getElementById('checkInPhoto');
    const photoPreview = document.getElementById('photoPreview');

    // 打卡功能事件監聽
    checkInFab.addEventListener('click', () => {
        if (currentStore && canCheckIn()) {
            openCheckInModal(currentStore);
        }
    });

    closeModal.addEventListener('click', closeCheckInModal);

    checkInModal.addEventListener('click', (e) => {
        if (e.target === checkInModal) {
            closeCheckInModal();
        }
    });

    ratingStars.forEach(star => {
        star.addEventListener('click', handleRatingClick);
    });

    photoInput.addEventListener('change', handlePhotoPreview);

    checkInForm.addEventListener('submit', handleCheckInSubmit);
}

init();
