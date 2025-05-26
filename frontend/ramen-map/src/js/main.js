import { GOOGLE_MAPS_MAP_ID } from './config.js';

let map;
let marker;
let nameLabel;
let currentStore = null;

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
                    lat: store.latitude,
                    lng: store.longitude
                };

                // marker 內容只放圖片
                const markerContent = document.createElement("div");
                markerContent.className = "marker-content";

                // 圖片
                const ramenImg = document.createElement("img");
                ramenImg.src = "/images/ramen-marker.png";
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
                <img src="/data/${store.menu_image || ''}" alt="${store.name} 菜單" style="width:100%;max-width:350px;margin:10px auto 0;display:block;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.08);background:#fafafa;" />
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
}

// 隱藏打卡按鈕
function hideCheckInButton() {
    currentStore = null;
    checkInFab.classList.remove('active');
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

    canvas.width = 300;
    canvas.height = 300;

    let ramenStores = [];
    let currentRotation = 0;
    let isSpinning = false;
    let selectedStore = null;

    fetch('/data/ramen.json')
        .then(response => response.json())
        .then(data => {
            ramenStores = data.ramen_stores;
            drawWheel();
        })
        .catch(error => console.error('Error loading ramen data:', error));

    function drawWheel() {
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 10;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const anglePerSlice = (2 * Math.PI) / ramenStores.length;
        
        ramenStores.forEach((store, index) => {
            const startAngle = index * anglePerSlice + currentRotation;
            const endAngle = (index + 1) * anglePerSlice + currentRotation;
            
            // 使用三種日本傳統色彩輪替，確保最後一片與前一片和第一片不同
            const colors = ['#E87A90', '#88C9A1', '#F7B977'];  // 櫻色、若竹色、山吹色
            let colorIndex;
            if (index === ramenStores.length - 1) {
                // 最後一片：選擇與前一片和第一片不同的顏色
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
        if (isSpinning) return;
        
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
                
                const anglePerSlice = (2 * Math.PI) / ramenStores.length;
                const pointerAngle = -Math.PI / 2;
                let idx = ((pointerAngle - currentRotation) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) / anglePerSlice;
                const selectedIndex = Math.floor(idx);
                selectedStore = ramenStores[selectedIndex];
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
        if (!isSpinning) {
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
            const position = {
                lat: selectedStore.latitude,
                lng: selectedStore.longitude
            };
            
            // 計算新的中心點，將標記放在地圖中間偏上的位置
            const newCenter = {
                lat: position.lat - 0.0015, // 向上偏移約150公尺
                lng: position.lng
            };
            
            map.panTo(newCenter);
            map.setZoom(16);
        
            renderStoreInfo(selectedStore);
            showCheckInButton(selectedStore);

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

// 初始化所有功能
function init() {
    initMap();
    initWheel();

    // 打卡功能事件監聽
    checkInFab.addEventListener('click', () => {
        if (currentStore) {
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
            rating: ratingInput.value,
            comment: document.getElementById('storeComment').value,
            photo: photoInput.files[0]
        };

        try {
            console.log('Form submitted:', formData);
            alert('打卡成功！');
            closeCheckInModal();
        } catch (error) {
            console.error('Error submitting form:', error);
            alert('提交失敗，請稍後再試');
        }
    });
}

init();
