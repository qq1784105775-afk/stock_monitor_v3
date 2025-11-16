/* 自选股监控 v3（Tushare 实盘 + 涨停榜 + 搜索全 A 股） */
let refreshInterval = 30000;
let soundOn = true;
const ALERT_COOLDOWN_MS = 10 * 60 * 1000;
const LS_KEY = 'stock_monitor_list_v3';

const INITIAL_TICKERS = [
  "002142.SZ","600000.SS","601939.SS","600036.SS","601988.SS","002407.SZ","002240.SZ","000559.SZ","002430.SZ","603938.SS",
  "002249.SZ","600660.SS","002235.SZ","002639.SZ","002562.SZ","002202.SZ","000969.SZ","600382.SS","603659.SS","600745.SS",
  "002759.SZ","002451.SZ","300777.SZ","002679.SZ","002009.SZ","300769.SZ","600742.SS","600089.SS","601138.SS","000555.SZ",
  "002007.SZ","300223.SZ","688981.SS","002099.SZ","002300.SZ","688599.SS","601012.SS","001871.SZ","002181.SZ","601179.SS",
  "600744.SS","002709.SZ","002028.SZ","300616.SZ","002636.SZ","002603.SZ","600105.SS","000070.SZ","600376.SS","002317.SZ",
  "600438.SS","603906.SS","002466.SZ","300837.SZ","600580.SS","300342.SS","300446.SZ","002568.SZ","300347.SZ","002373.SZ",
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
  "模塑科技":"300446.SZ","深圳新星":"002568.SZ","超颖电子":"300347.SZ","海峡创新":"002373.SZ","大有能源":"601156.SS"
};

let monitored = [];
const lastAlertAt = {};
let charts = {};

const searchBox = document.getElementById('searchBox');
const manualRefreshBtn = document.getElementById('manualRefresh');
const toggleSoundBtn = document.getElementById('toggleSound');
const refreshSelect = document.getElementById('refreshSelect');
const stocksContainer = document.getElementById('stocks');
const statusEl = document.getElementById('status');
const summaryEl = document.getElementById('summaryBar');
const dingAudio = document.getElementById('dingAudio');
const showZtBtn = document.getElementById('showZt');
const ztPanel = document.getElementById('ztPanel');
const closeZtBtn = document.getElementById('closeZt');
const ztList = document.getElementById('ztList');

function escapeCode(code) {
  return code.replace(/[^a-zA-Z0-9]/g, '_');
}

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

function computeSignalAndFlags(snap, history) {
  let base = { sig: 0, strong: false, vol_ratio: 0, price_change: 0, limitUp: null, limitUpBreak: false };
  try {
    if (snap && typeof snap.prev === 'number' && snap.prev > 0) {
      const limitUp = snap.prev * 1.1;
      const cur = snap.cur || snap.prev;
      const high = snap.high || cur;
      const pc = (cur - snap.prev) / snap.prev;
      base.limitUp = limitUp;
      if (high >= limitUp * 0.999 && cur <= limitUp * 0.985) {
        base.limitUpBreak = true;
      }
      base.price_change = pc;
    }
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
      if (vol_ratio >= 1.8 && price_change > 0.008) { base.sig = 1; base.strong = true; return base; }
      if (vol_ratio >= 1.8 && price_change < -0.008) { base.sig = -1; base.strong = true; return base; }
      if (vol_ratio >= 1.5 && price_change > 0.005) { base.sig = 1; base.strong = false; return base; }
      if (vol_ratio >= 1.5 && price_change < -0.005) { base.sig = -1; base.strong = false; return base; }
      return base;
    } else if (snap) {
      const prev = snap.prev || snap.cur;
      const price_change = prev ? (snap.cur - prev) / prev : 0;
      base.price_change = price_change;
      base.vol_ratio = 1;
      if (price_change > 0.02) { base.sig = 1; base.strong = true; return base; }
      if (price_change < -0.02) { base.sig = -1; base.strong = true; return base; }
      return base;
    }
  } catch (e) {}
  return base;
}

function createCard(code, meta) {
  const div = document.createElement('div');
  div.className = 'stock';
  const ledClass = meta.sig === 1 ? 'green' : (meta.sig === -1 ? 'red' : 'yellow');
  const text = meta.sig === 1 ? '买入' : (meta.sig === -1 ? '卖出' : '观望');
  let extra = '';
  if (meta.limitUpBreak) extra = '（涨停炸板）';
  const mfText = meta.main_net_amount != null
    ? `主力净额：${(meta.main_net_amount / 10000).toFixed(1)} 万`
    : '主力净额：-';
  div.innerHTML = `
    <div class="stock-top">
      <div class="stock-left">
        <div class="stock-name">${meta.name || code}</div>
        <div class="stock-meta">
          ${code}
          　最新: ${meta.last != null ? Number(meta.last).toFixed(2) : '-'}
          　量比: ${meta.vol_ratio != null ? Number(meta.vol_ratio).toFixed(2) : '-'}
          　涨跌: ${(meta.price_change * 100).toFixed(2)}%
        </div>
        <div class="moneyflow">${mfText}</div>
      </div>
      <div class="stock-right">
        <div class="led ${ledClass}" title="${text}"></div>
        <div><strong>${text}${meta.strong ? '（强）' : ''}${extra}</strong></div>
      </div>
    </div>
    <div class="canvas-wrap"><canvas id="chart_${escapeCode(code)}" height="70"></canvas></div>
  `;
  return div;
}

function buildChart(code, history) {
  try {
    if (!history) return;
    const canvas = document.getElementById('chart_' + escapeCode(code));
    if (!canvas) return;
    if (charts[code]) { try { charts[code].destroy(); } catch (e) {} charts[code] = null; }
    const ctx = canvas.getContext('2d');
    const vols = history.indicators.quote[0].volume.slice(-5);
    const labels = history.timestamp.slice(-5).map(ts => {
      const d = new Date(ts * 1000);
      return `${d.getMonth() + 1}/${d.getDate()}`;
    });
    charts[code] = new Chart(ctx, {
      type: 'bar',
      data: { labels, datasets: [{ label: '成交量', data: vols }] },
      options: { plugins: { legend: { display: false } }, scales: { x: { display: true }, y: { display: false } } }
    });
  } catch (e) {}
}

function tryAlert(code, meta) {
  if (!soundOn) return;
  const now = Date.now();
  const last = lastAlertAt[code] || 0;
  if (now - last < ALERT_COOLDOWN_MS) return;
  if (!meta) return;

  let text = null;
  if (meta.limitUpBreak) {
    text = '涨停炸板，' + (meta.name || code);
  } else if (meta.strong && meta.sig === 1) {
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

function updateSummary(metas) {
  let strongBuys = [], buys = [], strongSells = [], sells = [], bombs = [];
  for (const [code, meta] of Object.entries(metas)) {
    const nm = meta.name || code;
    if (meta.limitUpBreak) bombs.push(nm);
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
  if (bombs.length) parts.push(`涨停炸板 ${bombs.length} 只：${bombs.join('，')}`);
  summaryEl.innerText = parts.length ? ('今日信号：' + parts.join(' ｜ ')) : '今日暂无明显信号';
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
      const sf = computeSignalAndFlags(sData, history);
      const lastFromHistory = history && history.indicators && history.indicators.quote
        ? history.indicators.quote[0].close.slice(-1)[0]
        : null;
      const mf = moneyflowRes[t] || null;
      metas[t] = {
        name: sData?.name || getNameByCode(t) || t,
        last: lastFromHistory != null ? lastFromHistory : (sData ? sData.cur : null),
        vol_ratio: sf.vol_ratio || 0,
        sig: sf.sig,
        strong: sf.strong,
        history: history,
        limitUpBreak: sf.limitUpBreak,
        price_change: sf.price_change || 0,
        main_net_amount: mf ? (mf.main_net_amount || 0) : null
      };
    }

    function rank(m) {
      if (m.limitUpBreak) return -1;
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

    stocksContainer.innerHTML = '';
    for (const t of monitored) {
      const meta = metas[t] || { name: getNameByCode(t) || t, last: null, vol_ratio: 0, sig: 0, strong: false, limitUpBreak: false };
      const card = createCard(t, meta);
      stocksContainer.appendChild(card);
      if (meta.history) buildChart(t, meta.history);
      tryAlert(t, meta);
    }

    updateSummary(metas);
    statusEl.innerText = '上次刷新：' + new Date().toLocaleTimeString();
  } catch (e) {
    console.error(e);
    statusEl.innerText = '刷新失败，请稍后再试';
  }
}

function getNameByCode(code) {
  for (const [k, v] of Object.entries(NAME_MAP)) {
    if (v === code) return k;
  }
  return null;
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

async function loadZtRanking() {
  try {
    ztList.innerHTML = '加载中...';
    const r = await fetch('/api/zt_ranking');
    if (!r.ok) {
      ztList.innerHTML = '加载失败';
      return;
    }
    const j = await r.json();
    if (!j.ok || !j.data || j.data.length === 0) {
      ztList.innerHTML = '今日暂无涨停数据';
      return;
    }
    ztList.innerHTML = '';
    j.data.forEach((row, idx) => {
      const div = document.createElement('div');
      div.className = 'zt-row';
      const name = row.name || row.ts_code;
      const code = row.ts_code;
      const pct = row.pct_chg != null ? Number(row.pct_chg).toFixed(2) + '%' : '-';
      const strength = row.strength != null ? Number(row.strength).toFixed(1) : '-';
      div.innerHTML = `
        <div class="zt-left">
          <div class="zt-name">${idx + 1}. ${name}</div>
          <div class="zt-meta">${code} ｜ 涨幅：${pct}</div>
        </div>
        <div class="zt-strength">${strength}</div>
      `;
      div.addEventListener('click', async () => {
        if (!monitored.includes(code)) {
          monitored.push(code);
          saveMonitored();
          await refreshAll();
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
      ztList.appendChild(div);
    });
  } catch (e) {
    console.error(e);
    ztList.innerHTML = '加载失败';
  }
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
showZtBtn && showZtBtn.addEventListener('click', () => {
  ztPanel.classList.remove('hidden');
  loadZtRanking();
});
closeZtBtn && closeZtBtn.addEventListener('click', () => {
  ztPanel.classList.add('hidden');
});

loadMonitored();
refreshAll();
window._autoRefresh && clearInterval(window._autoRefresh);
window._autoRefresh = setInterval(refreshAll, refreshInterval);
