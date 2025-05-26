import { retroStyle } from './mapStyles.js';
import { GOOGLE_MAPS_MAP_ID } from './config.js';

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
    // fetch('/data/ramen.json')
    // fetch('shops')
    fetch("https://linebot-fastapi-uhmi.onrender.com/shops")
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

                // 點擊 marker 時顯示店名
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
                });

                // 點擊地圖其他地方時隱藏店名
                map.addListener("click", () => {
                    const oldNameDiv = markerContent.querySelector('.marker-store-name');
                    if (oldNameDiv) {
                        markerContent.removeChild(oldNameDiv);
                    }
                    showDefaultPage();
                });
            });
        })
        .catch(error => console.error('Error loading ramen data:', error));
}

// 將詳細資訊渲染到右側欄
function renderStoreInfo(store) {
    const ramenItems = document.getElementById('ramenItems');
    const defaultPage = document.querySelector('.ramen-default-page');
    if (defaultPage) defaultPage.style.display = 'none';
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
}

// 點擊地圖空白處時，恢復 default page
function showDefaultPage() {
    const ramenItems = document.getElementById('ramenItems');
    const defaultPage = document.querySelector('.ramen-default-page');
    if (ramenItems) ramenItems.innerHTML = '';
    if (defaultPage) defaultPage.style.display = '';
}

function buildContent(store) {
    const content = document.createElement("div");
    content.classList.add("property");
    
    // 將營業時間轉換為更易讀的格式
    const openTime = store.open_time.split(';')[0].trim();
    
    content.innerHTML = `
        <div class="details">
            <div class="price">${store.name}</div>
            <div class="address">${store.address || ''}</div>
            <div class="features">
                <div>
                    <i class="fas fa-star" title="評分"></i>
                    <span class="fa-sr-only">評分</span>
                    <span>${store.rating}</span>
                </div>
                <div>
                    <i class="fas fa-tags" title="關鍵字"></i>
                    <span class="fa-sr-only">關鍵字</span>
                    <span>${store.keywords ? store.keywords.join('、') : ''}</span>
                </div>
            </div>
        </div>
    `;
    return content;
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

initMap();
