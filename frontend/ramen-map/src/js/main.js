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
                currentUser = data.user.display_name;
                updateLoginUI();
            } else {
                console.error('User not found:', data.message);
            }
        } catch (error) {
            console.error('Error checking login status:', error);
        }
    }
}

// 新增：更新登入UI
function updateLoginUI() {
    const loginButton = document.getElementById('loginButton');
    const userInfo = document.getElementById('userInfo');
    
    if (currentUser) {
        loginButton.style.display = 'none';
        userInfo.style.display = 'flex';
        userInfo.querySelector('.username').textContent = currentUser;
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
function searchStores(query, showToast = false, selectFirst = false) {
    const searchResults = allStores.filter(store => 
        store.name.toLowerCase().includes(query.toLowerCase()) ||
        store.address.toLowerCase().includes(query.toLowerCase()) ||
        (store.keywords && store.keywords.some(keyword => 
            keyword.toLowerCase().includes(query.toLowerCase())
        ))
    );

    const searchResultsList = document.getElementById('searchResults');
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
                selectStore(store);
                searchResultsList.style.display = 'none';
            });
            searchResultsList.appendChild(resultItem);

            // 如果是第一個結果且需要選中，則選中它
            if (index === 0 && selectFirst) {
                selectStore(store);
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

// 新增：處理所有 URL 參數
function handleUrlParameters() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // 1. 處理登入狀態 - 移到 checkLoginStatus 函式中
    
    // 2. 處理轉盤店家列表
    const idsParam = urlParams.get("store_ids");
    if (idsParam) {
        storeEvents.on('storesLoaded', (stores) => {
            const ramenIds = idsParam.split(",");
            wheelStores = stores.filter(store => ramenIds.includes(store.id));
        });
    } else {
        wheelStores = [];
    }
    
    // 3. 處理是否顯示轉盤
    const showWheel = urlParams.get("show_wheel");
    if (showWheel === "1") {
        setTimeout(() => {
            document.getElementById('wheelModal').classList.add('active');
            document.body.classList.add('modal-open');
            if (typeof drawWheel === "function") drawWheel();
        }, 600);
    }
    
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
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControl: true,
    });

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
                ramenImg.src = "./src/assets/images/ramen-marker.png";
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
    ramenItems.innerHTML = `
        <div class="store-info-full">
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
                <div class="store-value">${store.keywords ? store.keywords.join('、') : ''}</div>
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
    `;

    ramenList.classList.add('active');
    ramenList.style.transform = 'translateY(0)';
    ramenList.style.maxHeight = 'var(--panel-height)';
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

// 拉麵轉盤功能
function initWheel() {
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

    function drawWheel() {
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 10;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (wheelStores.length === 0) {
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
    }

    function spinWheel() {
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
    }

    wheelFab.addEventListener('click', () => {
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

// 初始化所有功能
async function init() {
    initMap();
    initWheel();

    // 檢查登入狀態
    await checkLoginStatus();

    // 新增：搜尋功能初始化
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

    checkInForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!currentStore) {
            alert('請先選擇一家拉麵店');
            return;
        }

        const formData = {
            store_id: currentStore.id,
            user_id: currentUser,
            rating: parseFloat(ratingInput.value),
            comment: document.getElementById('storeComment').value
        };

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
            } else {
                // 修改錯誤處理邏輯
                const errorMessage = result.detail || '提交失敗';
                showToast(errorMessage);
                console.error('Error submitting form:', errorMessage);
                
            }
        } catch (error) {
            console.error('Error submitting form:', error.message || error);
            showToast('提交失敗，請稍後再試');
        }
    });
    // 處理所有 URL 參數
    handleUrlParameters();
}

init();
