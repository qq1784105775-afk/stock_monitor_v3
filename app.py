* 自选股量化终端 v3.1 - 专业终端布局（左表右详情） */
let refreshInterval = 30000;
let soundOn = true;
const ALERT_COOLDOWN_MS = 10 * 60 * 1000;
const LS_KEY = 'stock_monitor_list_v3_1';

const INITIAL_TICKERS = [
  "002142.SZ","600000.SS","601939.SS","600036.SS","601988.SS","002407.SZ","002240.SZ","000559.SZ","002430.SZ","603938.SS",
  "002249.SZ","600660.SS","002235.SZ","002639.SZ","002562.SZ","002202.SZ","000969.SZ","600382.SS","603659.SS","600745.SS",
  "002759.SZ","002451.SZ","300777.SZ","002679.SZ","002009.SZ","300769.SZ","600742.SS","600089.SS","601138.SS","000555.SZ",
  "002007.SZ","300223.SZ","688981.SS","002099.SZ","002300.SZ","688599.SS","601012.SS","001871.SZ","002181.SZ","601179.SS",
  "600744.SS","002709.SZ","002028.SZ","300616.SZ","002636.SZ","002603.SZ","600105.SS","000070.SZ","600376.SS","002317.SZ",
  "600438.SS","603906.SS","002466.SZ","300837.SZ","600580.SS","300342.SS","300446.SS","002568.SZ","300347.SZ","002373.SZ",
  "601156.SS"
];

const NAME_MAP = {
  "宁波银行":"002142.SZ","浦发银行":"600000.SS","建设银行":"601939.SS","招商银行":"600036.SS","农业银行":"601988.SS",
  "多氟多":"002407.SZ","盛新锂能":"002240.SZ","万向前潮":"000559.SZ","杭氧股份":"002430.SZ","三孚股份":"603938.SS",
  "大洋电机":"002249.SZ","福龙马":"600660.SS","平潭发展":"002235.SZ","雪人集团":"002639.SZ","兄弟科技":"002562.SZ",
  "金风科技":"002202.SZ","安泰科技":"000969.SZ","广东明珠":"600382.SS","璞泰来":"603659.SS","闻泰科技":"600745.SS",
  "天际股份":"002759.SZ","摩恩电气":"002451.SZ","中简科技":"300777.SZ","福建金森":"002679.SZ","天奇股份":"002009.SZ",
  "方正电机":"300769.SZ","特变电工":"600089.SS","工业富联":"601138.SS","神舟信息":"000555.SZ","华兰疫苗":"002007.SZ",
  "飞龙股份":"300223.SZ","中芯国际":"688981.SS","海翔药业":"002099.SZ","天华新能":"002300.SZ","天合光能":"688599.SS",
  "隆基绿能":"601012.SS","阿特斯":"001871.SZ","粤传媒":"002181.SZ","中国西电":"601179.SS","华银电力":"600744.SS",
  "天赐材料":"002709.SZ","思源电气":"002028.SZ","海侠股份":"300616.SZ","金安国纪":"002636.SZ","以岭药业":"002603.SZ",
  "永鼎股份":"600105.SS","合富中国":"000070.SZ","首开股份":"600376.SS","众生药业":"002317.SZ","通威股份":"600438.SS",
  "龙蟠科技":"603906.SS","天齐锂业":"002466.SZ","凯美特气":"300837.SZ","卧龙电驱":"600580.SS","山高科技":"300342.SS",
  "模塑科技":"300446.SS","深圳新星":"002568.SZ","超颖电子":"300347.SZ","海峡创新":"002373.SZ","大有能源":"601156.SS"
};

let monitored = [];
const lastAlertAt = {};
let detailChart = null;
let selectedCode = null;

const searchBox = document.getElementById('searchBox');
const manualRefreshBtn = document.getElementById('manualRefresh');
const toggleSoundBtn = document.getElementById('toggleSound');
const refreshSelect = document.getElementById('refreshSelect');
const statusEl = document.getElementById('status');
const summaryEl = document.getElementById('summaryBar');
const tableBody = document.getElementById('stockTableBody');
const detailInfo = document.getElementById('detailInfo');
const dingAudio = document.getElementById('dingAudio');
const detailVolumeCanvas = document.getElementById('detailVolumeChart');

function loadMonitored() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr) && arr.length) {
        monitored = Array.from(new Set(arr));
        return;
      }
    }
  } catch (e) {}
  monitored = Array.from(new Set(INITIAL_TICKERS));
}

function saveMonitored() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(monitored));
  } catch (e) {}
}

async function fetchSnapshotBatch(tsCodes) {
  if (!tsCodes || tsCodes.length === 0) return {};
  try {
    const qs = encodeURIComponent(tsCodes.join(','));
    const r = await fetch(`/api/snapshot_batch?ts_codes=${qs}`);
    if (!r.ok) return {};
    const j = await r.json();
    return j.ok ? (j.data || {}) : {};
  } catch (e) {
    console.error('snapshot_batch error', e);
    return {};
  }
}

async function fetchHistory5d(ticker) {
  try {
    const r = await fetch(`/api/history5d?ts_code=${encodeURIComponent(ticker)}`);
    if (!r.ok) return null;
    const j = await r.json();
    if (j.ok && j.data) return j.data;
    return null;
  } catch (e) {
    console.error('history5d error', e);
    return null;
  }
}

async function fetchMoneyflow(tsCodes) {
  if (!tsCodes || tsCodes.length === 0) return {};
  try {
    const qs = encodeURIComponent(tsCodes.join(','));
    const r = await fetch(`/api/moneyflow_latest?ts_codes=${qs}`);
    if (!r.ok) return {};
    const j = await r.json();
    if (j.ok && j.data) return j.data;
    return {};
  } catch (e) {
    console.error('moneyflow error', e);
    return {};
  }
}

function computeSignal(snap, history, mf) {
  let base = { sig: 0, strong: false, vol_ratio: 0, price_change: 0 };
  try {
    if (history && history.indicators && history.indicators.quote) {
      const closes = history.indicators.quote[0].close;
      const vols = history.indicators.quote[0].volume;
      const n = closes.length;
      const today = closes[n - 1];
      const prev = closes[n - 2] || today;
      const today_vol = vols[n - 1] || 0;
      const avg5 = vols.slice(Math.max(0, n - 5), n).reduce((a, b) => a + (b || 0), 0) / Math.min(5, n);
      const vol_ratio = avg5 ? today_vol / avg5 : 1;
      const price_change = prev ? (today - prev) / prev : 0;
      base.vol_ratio = vol_ratio;
      base.price_change = price_change;
    } else if (snap) {
      const prev = snap.prev || snap.cur;
      const price_change = prev ? (snap.cur - prev) / prev : 0;
      base.price_change = price_change;
      base.vol_ratio = 1;
    }

    const mainNet = mf ? (mf.main_net_amount || 0) : 0;

    if (base.vol_ratio >= 1.8 && base.price_change > 0.008 && mainNet > 0) {
      base.sig = 1;
      base.strong = true;
      return base;
    }
    if (base.vol_ratio >= 1.8 && base.price_change < -0.008 && mainNet < 0) {
      base.sig = -1;
      base.strong = true;
      return base;
    }
    if (base.vol_ratio >= 1.3 && base.price_change > 0.004 && mainNet > 0) {
      base.sig = 1;
      base.strong = false;
      return base;
    }
    if (base.vol_ratio >= 1.3 && base.price_change < -0.004 && mainNet < 0) {
      base.sig = -1;
      base.strong = false;
      return base;
    }
    return base;
  } catch (e) {
    return base;
  }
}

function tryAlert(code, meta) {
  if (!soundOn) return;
  const now = Date.now();
  const last = lastAlertAt[code] || 0;
  if (now - last < ALERT_COOLDOWN_MS) return;
  if (!meta) return;

  let text = null;
  if (meta.strong && meta.sig === 1) {
    text = '强烈买入，' + (meta.name || code);
  } else if (meta.strong && meta.sig === -1) {
    text = '强烈卖出，' + (meta.name || code);
  }

  if (!text) return;
  lastAlertAt[code] = now;

  try { dingAudio && dingAudio.play().catch(() => {}); } catch (e) {}

  try {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'zh-CN';
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  } catch (e) {}
}

function getNameByCode(code) {
  for (const [k, v] of Object.entries(NAME_MAP)) {
    if (v === code) return k;
  }
  return null;
}

function updateSummary(metas) {
  let strongBuys = [], buys = [], strongSells = [], sells = [];
  for (const [code, meta] of Object.entries(metas)) {
    const nm = meta.name || code;
    if (meta.sig === 1 && meta.strong) strongBuys.push(nm);
    else if (meta.sig === 1) buys.push(nm);
    else if (meta.sig === -1 && meta.strong) strongSells.push(nm);
    else if (meta.sig === -1) sells.push(nm);
  }
  const parts = [];
  if (strongBuys.length) parts.push(`强烈买入 ${strongBuys.length} 只：${strongBuys.join('，')}`);
  if (buys.length) parts.push(`买入 ${buys.length} 只：${buys.join('，')}`);
  if (strongSells.length) parts.push(`强烈卖出 ${strongSells.length} 只：${strongSells.join('，')}`);
  if (sells.length) parts.push(`卖出 ${sells.length} 只：${sells.join('，')}`);
  summaryEl.innerText = parts.length ? ('今日信号：' + parts.join(' ｜ ')) : '今日暂无明显信号';
}

function renderTable(metas) {
  tableBody.innerHTML = '';
  monitored.forEach(code => {
    const m = metas[code] || {};
    const tr = document.createElement('tr');
    if (code === selectedCode) tr.classList.add('active');

    let ledClass = 'yellow';
    if (m.sig === 1) ledClass = 'green';
    else if (m.sig === -1) ledClass = 'red';

    const pc = (m.price_change || 0) * 100;
    const pcStr = pc ? pc.toFixed(2) + '%' : '-';
    const volStr = m.vol_ratio != null ? Number(m.vol_ratio).toFixed(2) : '-';
    const mfStr = m.main_net_amount != null ? (m.main_net_amount / 10000).toFixed(1) : '-';

    const name = m.name || getNameByCode(code) || code;

    tr.innerHTML = `
      <td><span class="led ${ledClass}"></span>${m.strong ? '★' : ''}</td>
      <td>${name}</td>
      <td>${code}</td>
      <td>${m.last != null ? Number(m.last).toFixed(2) : '-'}</td>
      <td>${pcStr}</td>
      <td>${volStr}</td>
      <td>${mfStr}</td>
    `;

    tr.addEventListener('click', () => {
      selectedCode = code;
      renderTable(metas);
      renderDetail(code, m);
    });

    tableBody.appendChild(tr);
  });
}

function renderDetail(code, meta) {
  const name = meta.name || getNameByCode(code) || code;
  const pc = (meta.price_change || 0) * 100;
  const pcStr = pc ? pc.toFixed(2) + '%' : '-';
  const volStr = meta.vol_ratio != null ? Number(meta.vol_ratio).toFixed(2) : '-';
  const mfStr = meta.main_net_amount != null ? (meta.main_net_amount / 10000).toFixed(1) + ' 万' : '-';

  let sigText = '观望';
  if (meta.sig === 1 && meta.strong) sigText = '强烈买入';
  else if (meta.sig === 1) sigText = '买入';
  else if (meta.sig === -1 && meta.strong) sigText = '强烈卖出';
  else if (meta.sig === -1) sigText = '卖出';

  detailInfo.innerHTML = `
    <div class="detail-line"><strong>${name}</strong>（${code}）</div>
    <div class="detail-line">当前价：${meta.last != null ? Number(meta.last).toFixed(2) : '-'}　涨跌：${pcStr}</div>
    <div class="detail-line">量比：${volStr}　主力净额：${mfStr}</div>
    <div class="detail-line">信号：${sigText}</div>
    <div class="detail-line" style="margin-top:4px;font-size:11px;color:#9ca3af;">
      参考规则：<br>
      · 🟢 买入：放量 + 主力净流入 + 价格上攻<br>
      · 🔴 卖出：放量下跌 + 主力净流出<br>
      · “强烈”代表信号更可靠，适合短线操作
    </div>
  `;

  if (detailChart) {
    try { detailChart.destroy(); } catch (e) {}
    detailChart = null;
  }
  const history = meta.history;
  if (!history || !history.indicators || !history.indicators.quote) return;
  try {
    const vols = history.indicators.quote[0].volume.slice(-5);
    const labels = history.timestamp.slice(-5).map(ts => {
      const d = new Date(ts * 1000);
      return `${d.getMonth() + 1}/${d.getDate()}`;
    });
    const ctx = detailVolumeCanvas.getContext('2d');
    detailChart = new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets: [{ label: '成交量', data: vols }] },
      options: { plugins: { legend: { display: false } }, scales: { x: { display: true }, y: { display: false } } }
    });
  } catch (e) {}
}

async function refreshAll() {
  statusEl.innerText = '刷新中... ' + new Date().toLocaleTimeString();
  try {
    const snapRes = await fetchSnapshotBatch(monitored);
    const historyMap = {};
    await Promise.all(monitored.map(async t => {
      historyMap[t] = await fetchHistory5d(t).catch(() => null);
    }));
    const moneyflowRes = await fetchMoneyflow(monitored);

    const metas = {};

    for (const t of monitored) {
      const sData = snapRes[t] || null;
      const history = historyMap[t] || null;
      const mf = moneyflowRes[t] || null;
      const sf = computeSignal(sData, history, mf);
      const lastFromHistory = history && history.indicators && history.indicators.quote
        ? history.indicators.quote[0].close.slice(-1)[0]
        : null;
      metas[t] = {
        name: sData?.name || getNameByCode(t) || t,
        last: lastFromHistory != null ? lastFromHistory : (sData ? sData.cur : null),
        vol_ratio: sf.vol_ratio || 0,
        sig: sf.sig,
        strong: sf.strong,
        history: history,
        price_change: sf.price_change || 0,
        main_net_amount: mf ? (mf.main_net_amount || 0) : null
      };
    }

    function rank(m) {
      if (m.sig === 1 && m.strong) return 0;
      if (m.sig === 1) return 1;
      if (m.sig === -1 && m.strong) return 2;
      if (m.sig === -1) return 3;
      return 4;
    }

    monitored.sort((a, b) => {
      const A = metas[a] || { sig: 0, strong: false, vol_ratio: 0 };
      const B = metas[b] || { sig: 0, strong: false, vol_ratio: 0 };
      const rA = rank(A), rB = rank(B);
      if (rA !== rB) return rA - rB;
      return (B.vol_ratio || 0) - (A.vol_ratio || 0);
    });

    renderTable(metas);
    updateSummary(metas);

    if (selectedCode && metas[selectedCode]) {
      renderDetail(selectedCode, metas[selectedCode]);
    }

    for (const [code, meta] of Object.entries(metas)) {
      if (meta.sig !== 0 && meta.strong) {
        tryAlert(code, meta);
      }
    }

    statusEl.innerText = '上次刷新：' + new Date().toLocaleTimeString();
  } catch (e) {
    console.error(e);
    statusEl.innerText = '刷新失败，请稍后再试';
  }
}

async function addByKeyword(keyword) {
  keyword = keyword.trim();
  if (!keyword) return;

  if (/^\d{6}(\.(SZ|SS|SH))?$/i.test(keyword) || /^[a-z]{2}\d{6}$/i.test(keyword)) {
    let k = keyword.toUpperCase();
    if (/^\d{6}$/.test(k)) k = (k.startsWith('6') ? k + '.SS' : k + '.SZ');
    if (!monitored.includes(k)) monitored.push(k);
    saveMonitored();
    await refreshAll(); return;
  }

  if (NAME_MAP[keyword]) {
    const code = NAME_MAP[keyword];
    if (!monitored.includes(code)) monitored.push(code);
    saveMonitored();
    await refreshAll(); return;
  }

  try {
    const r = await fetch(`/api/search_stock?q=${encodeURIComponent(keyword)}`);
    if (r.ok) {
      const j = await r.json();
      if (j.ok && j.data && j.data.length > 0) {
        const code = j.data[0].ts_code;
        if (code && !monitored.includes(code)) {
          monitored.push(code);
          saveMonitored();
          await refreshAll();
          return;
        }
      }
    }
  } catch (e) {
    console.error('search_stock error', e);
  }

  alert('未识别该名称，请输入更精确中文名或代码（例如 002142.SZ 或 宁波银行）');
}

manualRefreshBtn && manualRefreshBtn.addEventListener('click', refreshAll);
toggleSoundBtn && toggleSoundBtn.addEventListener('click', () => {
  soundOn = !soundOn;
  toggleSoundBtn.innerText = soundOn ? '声音：开' : '声音：关';
});
refreshSelect && refreshSelect.addEventListener('change', (e) => {
  clearInterval(window._autoRefresh);
  refreshInterval = parseInt(e.target.value);
  window._autoRefresh = setInterval(refreshAll, refreshInterval);
});
searchBox && searchBox.addEventListener('keydown', async (e) => {
  if (e.key === 'Enter') {
    const v = e.target.value.trim();
    if (v) {
      await addByKeyword(v);
      e.target.value = '';
    }
  }
});

loadMonitored();
refreshAll();
window._autoRefresh && clearInterval(window._autoRefresh);
window._autoRefresh = setInterval(refreshAll, refreshInterval);
