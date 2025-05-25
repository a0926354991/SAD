import { retroStyle } from './mapStyles.js';
import { GOOGLE_MAPS_MAP_ID } from './config.js';
import { initCheckIn, showCheckInButton, hideCheckInButton } from './checkIn.js';

let map;
let marker;
let nameLabel;

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
        // 隱藏預設的地點標記
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControl: true,
    });

    // 讀取拉麵店資料
    fetch('/data/ramen.json')
        .then(response => response.json())
        .then(data => {
            data.ramen_stores.forEach(store => {
                const position = {
                    lat: store.coordinates.lat,
                    lng: store.coordinates.lng
                };

                // marker 內容只放圖片
                const markerContent = document.createElement("div");
                markerContent.className = "marker-content";

                // 圖片
                const ramenImg = document.createElement("img");
                ramenImg.src = "/images/ramen-marker.png";
                ramenImg.className = "ramen-marker-img";

                markerContent.appendChild(ramenImg);

                // 建立 marker
                const marker = new AdvancedMarkerElement({
                    map,
                    position,
                    content: markerContent,
                    title: store.name,
                    gmpClickable: true
                });

                // 點擊 marker 時顯示店名和打卡按鈕
                marker.addListener("gmp-click", () => {
                    // 檢查是否已有店名顯示
                    const oldNameDiv = markerContent.querySelector('.marker-store-name');
                    if (!oldNameDiv) {
                        // 如果沒有店名，則新增它
                        const nameDiv = document.createElement("div");
                        nameDiv.textContent = store.name;
                        nameDiv.className = "marker-store-name";
                        markerContent.appendChild(nameDiv);
                    }
                    renderStoreInfo(store);
                    panMapToSafeBounds(map, position);
                    showCheckInButton(store);
                });

                // 點擊地圖其他地方時隱藏店名和打卡按鈕
                map.addListener("click", () => {
                    const oldNameDiv = markerContent.querySelector('.marker-store-name');
                    if (oldNameDiv) {
                        markerContent.removeChild(oldNameDiv);
                    }
                    showDefaultPage();
                    hideCheckInButton();
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

  // 如果向下滾動，展開面板
  if (scrollDirection === 'down') {
    ramenList.classList.add('active');
    ramenList.style.transform = 'translateY(0)';
    ramenList.style.maxHeight = '80vh';
  }

  lastScrollTop = currentScroll;

  // 設置滾動結束的延遲
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
                <img src="/data/${store.menu_image || ''}" alt="${store.name} 菜單" style="width:100%;max-width:350px;margin:10px auto 0;display:block;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);background:#fafafa;" />
            </div>
        </div>
    `;

    // 自動展開底部面板
    ramenList.classList.add('active');
    ramenList.style.transform = 'translateY(0)';
    ramenList.style.maxHeight = 'var(--panel-height)';
}

// 點擊地圖空白處時，恢復預設狀態
function showDefaultPage() {
    const ramenItems = document.getElementById('ramenItems');
    if (ramenItems) ramenItems.innerHTML = '';

    // 收起底部面板
    ramenList.classList.remove('active');
    ramenList.style.transform = 'translateY(calc(100% - 50px))';
    ramenList.style.maxHeight = 'var(--panel-height)';
}

// 檢查並移動地圖，確保標記在安全範圍內
function panMapToSafeBounds(map, position) {
    const bounds = map.getBounds();
    if (!bounds) return;

    const ne = bounds.getNorthEast();
    const sw = bounds.getSouthWest();
    const latPadding = (ne.lat() - sw.lat()) * 0.2; // 上下留 20% 的安全範圍
    const lngPadding = (ne.lng() - sw.lng()) * 0.2; // 左右留 20% 的安全範圍

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
        // 計算新的中心點，讓標記剛好進入安全範圍
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

// Modal functionality
const checkInFab = document.getElementById('checkInFab');
const checkInModal = document.getElementById('checkInModal');
const closeModal = document.querySelector('.close-modal');
const checkInForm = document.getElementById('checkInForm');

// Open modal
checkInFab.addEventListener('click', () => {
    checkInModal.classList.add('active');
    document.body.classList.add('modal-open');
});

// Close modal
function closeCheckInModal() {
    checkInModal.classList.remove('active');
    document.body.classList.remove('modal-open');
    checkInForm.reset(); // Reset form
}

closeModal.addEventListener('click', closeCheckInModal);

// Close modal when clicking outside
checkInModal.addEventListener('click', (e) => {
    if (e.target === checkInModal) {
        closeCheckInModal();
    }
});

// Handle form submission
checkInForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('storeName').value,
        address: document.getElementById('storeAddress').value,
        rating: document.getElementById('storeRating').value,
        keywords: document.getElementById('storeKeywords').value.split(',').map(k => k.trim()),
        open_time: document.getElementById('storeOpenTime').value,
        menu_image: document.getElementById('storeMenu').files[0]
    };

    try {
        // Here you would typically send the data to your backend
        console.log('Form submitted:', formData);
        
        // For now, just show a success message
        alert('打卡成功！');
        closeCheckInModal();
    } catch (error) {
        console.error('Error submitting form:', error);
        alert('提交失敗，請稍後再試');
    }
});

// 初始化所有功能
function init() {
    initMap();
    initCheckIn();
}

init();
