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

let currentStore = null;

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
    currentStore = null;
    // 重置評分星星
    ratingStars.forEach(star => star.classList.remove('active'));
}

// 處理評分星星點擊
function handleRatingClick(e) {
    const rating = parseInt(e.target.dataset.rating);
    ratingInput.value = rating;
    
    // 更新星星顯示
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

// 初始化打卡功能
function initCheckIn() {
    // 點擊 FAB 開啟打卡頁面
    checkInFab.addEventListener('click', () => {
        if (currentStore) {
            openCheckInModal(currentStore);
        }
    });

    // 點擊關閉按鈕關閉打卡頁面
    closeModal.addEventListener('click', closeCheckInModal);

    // 點擊背景關閉打卡頁面
    checkInModal.addEventListener('click', (e) => {
        if (e.target === checkInModal) {
            closeCheckInModal();
        }
    });

    // 評分星星點擊事件
    ratingStars.forEach(star => {
        star.addEventListener('click', handleRatingClick);
    });

    // 照片預覽
    photoInput.addEventListener('change', handlePhotoPreview);

    // 處理表單提交
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
            // 這裡之後會發送資料到後端
            console.log('Form submitted:', formData);
            
            // 暫時只顯示成功訊息
            alert('打卡成功！');
            closeCheckInModal();
        } catch (error) {
            console.error('Error submitting form:', error);
            alert('提交失敗，請稍後再試');
        }
    });
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

// 匯出需要的函數
export {
    initCheckIn,
    openCheckInModal,
    closeCheckInModal,
    showCheckInButton,
    hideCheckInButton
}; 