// easeInOutQuad，加速再減速
function easeInOutQuad(t) {
    return t < 0.5
      ? 2 * t * t
      : -1 + (4 - 2 * t) * t;
  }

// 1. 抓元素
const canvas  = document.getElementById('wheelCanvas');
const ctx     = canvas.getContext('2d');
const spinBtn = document.getElementById('spinBtn');
const resultP = document.getElementById('result');
const radius  = canvas.width / 2;

function getCheckedValues(groupId) {
  return Array.from(document.querySelectorAll(`#${groupId} input:checked`)).map(cb => cb.value);
}

function applyFilters() {
  const flavors = getCheckedValues('flavorGroup');
  const distances = getCheckedValues('distanceGroup');
  const budgets = getCheckedValues('budgetGroup');

  const filtered = ramenData.filter(item => {
    return (flavors.length === 0 || flavors.includes(item.flavor)) &&
           (distances.length === 0 || distances.includes(item.distance)) &&
           (budgets.length === 0 || budgets.includes(item.budget));
  });

  ramenList = filtered.map(item => item.name);
  drawWheel(ramenList);
  document.getElementById('result').textContent = '';
}



// 2. 載入 JSON 資料並畫轉盤
let ramenData = []; // 全部資料
let ramenList = []; // 篩選後 name 名單
fetch('ramen_shop.json')
  .then(res => res.json())
  .then(data => {
    // ramenList = data.map(item => item.name);  // 只取 name 欄位
    ramenData = data;
    applyFilters(); // 一開始直接畫出所有選項
    
    ['flavorGroup', 'distanceGroup', 'budgetGroup'].forEach(groupId => {
      document.querySelectorAll(`#${groupId} input`).forEach(cb => {
        cb.addEventListener('change', applyFilters);
      });
    });
  })
  .catch(err => {
    console.error('載入 ramen.json 失敗', err);
  });

// 3. 繪製轉盤函式
function drawWheel(list) {
  const n   = list.length;
  const arc = (2 * Math.PI) / n;

  // 先清空畫面
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 畫每一個扇形
  list.forEach((text, i) => {
    // 画扇形
    ctx.beginPath();
    ctx.fillStyle = i % 2 === 0 ? '#f1f5f9' : '#e2e8f0';
    ctx.moveTo(radius, radius);
    ctx.arc(radius, radius, radius, i * arc, (i + 1) * arc);
    ctx.fill();

    // 画文字
    ctx.save();
    ctx.translate(radius, radius);
    ctx.rotate(i * arc + arc / 2);
    ctx.textAlign = 'right';
    ctx.fillStyle = '#1e293b';
    ctx.font = '14px sans-serif';
    ctx.fillText(text, radius - 10, 5);
    ctx.restore();
  });
}

// // 4. 轉動+抽籤
// spinBtn.addEventListener('click', () => {
//   if (ramenList.length === 0) return;

//   const n      = ramenList.length;
//   const winner = Math.floor(Math.random() * n);
//   const spins  = 10;              // 轉幾圈
//   const degPer = 360 / n;
//   const finalDeg = degPer * winner + 360 * spins;

//   // 加上 CSS 動畫
//   canvas.style.transition = `transform 3s cubic-bezier(.33,1.4,.68,1)`;
//   canvas.style.transform  = `rotate(${finalDeg}deg)`;

//   // 動畫結束後顯示結果並重設角度
//   setTimeout(() => {
//     resultP.textContent = `你抽到了：${ramenList[winner]}`;
//     // 把畫布固定在停下來的位置，避免下一次角度錯亂
//     canvas.style.transition = 'none';
//     canvas.style.transform  = `rotate(${degPer * winner}deg)`;
//   }, 3000 + 50);
// });

// 隨機函式
function getRandomIndex(max) {
    const rand32 = window.crypto.getRandomValues(new Uint32Array(1))[0];
    return rand32 % max;
  }  

function spinTo(winnerIndex) {
    const n       = ramenList.length;
    const spins   = 10;                 // 想转几圈
    const degPer  = 360 / n;
    // 每块中心相对于 3 点钟的角度
    const sliceCenterDeg = winnerIndex * degPer + degPer / 2;
    // alignOffset=90°：把 3 点钟的 0° 对准 12 点钟
    const alignOffset     = 90;
    // 最终要把 sliceCenterDeg 逆时针转到 90°，再加上完整圈数
    const targetDeg       = spins * 360 + (alignOffset - sliceCenterDeg);

    animateSpin(targetDeg, 3000, () => {
    resultP.textContent = `你抽到了：${ramenList[winnerIndex]}`;
    });
}
  

spinBtn.addEventListener('click', () => {
    if (ramenList.length === 0) return;
  
    const n      = ramenList.length;
    const winner = getRandomIndex(n);
    spinTo(winner)
  });
  
/**
 * @param {number} targetDeg  總共要轉的度數
 * @param {number} duration   動畫時長 (ms)
 * @param {Function} callback 動畫結束時呼叫
 */

function animateSpin(targetDeg, duration, callback) {
    const start      = performance.now();
    const initialDeg = getCurrentRotation(); // 读当前旋转（0~360）

    function frame(now) {
    const elapsed = now - start;
    const t       = Math.min(elapsed / duration, 1);
    const eased   = easeInOutQuad(t);
    const current = initialDeg + (targetDeg - initialDeg) * eased;
    canvas.style.transform = `rotate(${current}deg)`;

    if (t < 1) {
        requestAnimationFrame(frame);
    } else {
        // 确保精确到目标角度
        canvas.style.transform = `rotate(${targetDeg}deg)`;
        callback?.();
    }
    }
    requestAnimationFrame(frame);
}
  
/** 讀出 <canvas> 當前的 rotate(deg) */
function getCurrentRotation() {
    const st = getComputedStyle(canvas);
    const tr = st.transform || '';
    if (tr.startsWith('matrix')) {
      const vals = tr.match(/matrix\(([^)]+)\)/)[1].split(', ');
      const a = parseFloat(vals[0]), b = parseFloat(vals[1]);
      let angle = Math.atan2(b, a) * 180 / Math.PI;
      return (angle + 360) % 360;
    }
    return 0;
}
  
const filterModal = document.getElementById('filterModal');

document.getElementById('openFilterBtn').addEventListener('click', () => {
  filterModal.classList.remove('hidden');
});

document.getElementById('closeFilterBtn').addEventListener('click', () => {
  filterModal.classList.add('hidden');
});

document.getElementById('confirmFilterBtn').addEventListener('click', () => {
  filterModal.classList.add('hidden');
  applyFilters(); // ✅ 套用篩選
});
