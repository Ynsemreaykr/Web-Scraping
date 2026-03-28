/* ── app.js ─────────────────────────────────────────────────────
   Ana uygulama state ve ortak fonksiyonlar
──────────────────────────────────────────────────────────────── */

const API_BASE = 'http://localhost:5000/api';

// Uygulama state
const state = {
  allNews: [],      // tum cekilmis haberler
  filtered: [],     // filtre uygulanmis haberler
  category: '',     // aktif kategori filtresi
  district: '',     // aktif ilce filtresi
  dateFrom: '',
  dateTo: '',
  onlyMapped: false,
  mapReady: false,
};

// Kategori renk paleti
const CATEGORY_COLORS = {
  'Trafik Kazasi':        { color: '#da3131', icon: '🚗', label: 'Trafik Kazası' },
  'Yangin':               { color: '#e8762b', icon: '🔥', label: 'Yangın' },
  'Elektrik Kesintisi':   { color: '#d4b700', icon: '⚡', label: 'Elektrik Kesintisi' },
  'Hirsizlik':            { color: '#5c6bc0', icon: '🔒', label: 'Hırsızlık' },
  'Kulturel Etkinlikler': { color: '#2e9e44', icon: '🎭', label: 'Kültürel Etkinlikler' },
};

// ── Başlangıç ──────────────────────────────────────────────────
async function initApp() {
  try {
    // Config'i API'den al (Google API key dahil)
    const cfg = await fetchJSON(`${API_BASE}/config`);
    window.GOOGLE_API_KEY = cfg.data.googleApiKey;
    window.KOCAELI_CENTER = cfg.data.kocaeliCenter;

    // Google Maps'i yükle
    loadGoogleMaps(cfg.data.googleApiKey);

    // Filtre seçeneklerini doldur
    await loadCategories();
    await loadDistricts();

    // İstatistikleri al
    loadStats();

    // Haberleri yükle
    await loadNews();

  } catch (err) {
    showToast('Backend bağlantısı kurulamadı. Flask çalışıyor mu?', 'error');
    console.error('initApp hatası:', err);
  }
}

// ── API Yardımcıları ───────────────────────────────────────────
async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Haberleri Yükle ───────────────────────────────────────────
async function loadNews() {
  showListLoading(true);
  try {
    const params = new URLSearchParams();
    if (state.category)   params.set('category', state.category);
    if (state.district)   params.set('district', state.district);
    if (state.dateFrom)   params.set('date_from', state.dateFrom);
    if (state.dateTo)     params.set('date_to', state.dateTo);
    if (state.onlyMapped) params.set('has_location', 'true');

    const data = await fetchJSON(`${API_BASE}/news?${params}`);
    state.allNews = data.data || [];
    state.filtered = state.allNews;

    renderNewsList(state.filtered);
    if (state.mapReady) {
      renderMarkers(state.filtered);
    }
    document.getElementById('newsCount').textContent = state.filtered.length;
    loadStats();
  } catch (err) {
    showListLoading(false);
    console.error('Haberler yüklenemedi:', err);
  }
}

// ── Filtre Uygula ─────────────────────────────────────────────
function applyFilters() {
  state.district   = document.getElementById('districtSelect').value;
  state.dateFrom   = document.getElementById('dateFrom').value;
  state.dateTo     = document.getElementById('dateTo').value;
  state.onlyMapped = document.getElementById('onlyMapped').checked;
  loadNews();
}

function setCategory(btn, cat) {
  state.category = cat;
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  loadNews();
}

function resetFilters() {
  state.category = '';
  state.district = '';
  state.dateFrom = '';
  state.dateTo = '';
  state.onlyMapped = false;
  document.getElementById('districtSelect').value = '';
  document.getElementById('dateFrom').value = '';
  document.getElementById('dateTo').value = '';
  document.getElementById('onlyMapped').checked = false;
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  document.querySelector('.chip[data-category=""]').classList.add('active');
  loadNews();
}

// ── Kategori Chips ────────────────────────────────────────────
async function loadCategories() {
  try {
    const data = await fetchJSON(`${API_BASE}/categories`);
    const container = document.getElementById('categoryChips');
    data.data.forEach(cat => {
      const info = CATEGORY_COLORS[cat.key] || {};
      const btn = document.createElement('button');
      btn.className = 'chip';
      btn.dataset.category = cat.key;
      btn.textContent = `${info.icon || ''} ${cat.display}`;
      btn.onclick = () => setCategory(btn, cat.key);
      container.appendChild(btn);
    });

    // Lejant
    buildLegend(data.data);
  } catch (err) {
    console.error('Kategoriler yüklenemedi:', err);
  }
}

function buildLegend(categories) {
  const legend = document.getElementById('mapLegend');
  categories.forEach(cat => {
    const info = CATEGORY_COLORS[cat.key] || { color: '#888', icon: '•' };
    const item = document.createElement('div');
    item.className = 'legend-item';
    item.innerHTML = `
      <div class="legend-dot" style="background:${info.color}"></div>
      <span>${info.icon} ${cat.display}</span>
    `;
    legend.appendChild(item);
  });
}

// ── İlçe Dropdown ────────────────────────────────────────────
async function loadDistricts() {
  try {
    const data = await fetchJSON(`${API_BASE}/districts`);
    const sel = document.getElementById('districtSelect');
    data.data.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.error('İlçeler yüklenemedi:', err);
  }
}

// ── İstatistik ────────────────────────────────────────────────
async function loadStats() {
  try {
    const data = await fetchJSON(`${API_BASE}/stats`);
    document.getElementById('statTotal').textContent  = `${data.data.total} haber`;
    document.getElementById('statMapped').textContent = `${data.data.mapped} haritada`;
  } catch (err) {}
}

// ── Scraping Tetikle ──────────────────────────────────────────
async function triggerScrape() {
  const btn = document.getElementById('btnScrape');
  const label = document.getElementById('scrapeLabel');
  if (btn.classList.contains('loading')) return;

  btn.classList.add('loading');
  label.textContent = 'Kazınıyor...';
  showToast('Scraping başlatıldı. Bu birkaç dakika sürebilir...', 'info');

  try {
    await fetchJSON(`${API_BASE}/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    // Durum sorgula
    pollScrapeStatus();
  } catch (err) {
    btn.classList.remove('loading');
    label.textContent = 'Haberleri Güncelle';
    showToast('Scraping başlatılamadı.', 'error');
  }
}

function pollScrapeStatus() {
  const interval = setInterval(async () => {
    try {
      const data = await fetchJSON(`${API_BASE}/scrape/status`);
      if (!data.data.running) {
        clearInterval(interval);
        const btn = document.getElementById('btnScrape');
        const label = document.getElementById('scrapeLabel');
        btn.classList.remove('loading');
        label.textContent = 'Haberleri Güncelle';
        const stats = data.data.last_stats || {};
        showToast(`✅ Tamamlandı! ${stats.saved || 0} yeni haber kaydedildi.`, 'success');
        await loadNews();
      }
    } catch (err) {
      clearInterval(interval);
    }
  }, 3000);
}

// ── Haber Listesi Render ──────────────────────────────────────
function renderNewsList(newsList) {
  showListLoading(false);
  const container = document.getElementById('newsList');

  if (!newsList.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔍</div>
        <p>Bu filtreye uygun haber bulunamadı.</p>
      </div>`;
    document.getElementById('newsCount').textContent = '0';
    return;
  }

  container.innerHTML = newsList.map(n => {
    const cat = n.category || '';
    const catInfo = CATEGORY_COLORS[cat] || { icon: '📰', label: cat };
    const hasLoc = n.location && n.location.lat;
    const dateStr = n.published_at ? new Date(n.published_at).toLocaleDateString('tr-TR') : '—';
    const catClass = cat.replace(/\s+/g, '-');
    const source = (n.sources && n.sources[0]) ? n.sources[0].source_name : (n.source_name || '');
    // Tum kaynaklar
    const allSources = n.sources ? n.sources.map(s => s.source_name).join(', ') : source;

    return `
      <div class="news-card" data-cat="${cat}" data-id="${n._id}"
           onclick="onCardClick('${n._id}', ${hasLoc ? n.location.lat : 'null'}, ${hasLoc ? n.location.lng : 'null'})">
        <div class="card-meta">
          <span class="cat-badge ${catClass}">${catInfo.icon} ${catInfo.label}</span>
          <span class="card-date">${dateStr}</span>
        </div>
        <div class="card-title">${escHtml(n.title)}</div>
        <div class="card-source">
          <span class="card-loc-icon">${hasLoc ? '📍' : '📌'}</span>
          <span>${escHtml(allSources)}</span>
          ${!hasLoc ? '<span class="no-map-badge">Haritasız</span>' : ''}
        </div>
      </div>`;
  }).join('');

  document.getElementById('newsCount').textContent = newsList.length;
}

function onCardClick(id, lat, lng) {
  if (lat && lng && state.mapReady) {
    panToMarker(id, lat, lng);
  }
}

// ── Yardımcılar ───────────────────────────────────────────────
function showListLoading(show) {
  if (show) {
    document.getElementById('newsList').innerHTML = `
      <div class="loading-placeholder">
        <div class="spinner"></div>
        <p>Yükleniyor...</p>
      </div>`;
  }
}

function showToast(msg, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = `toast show ${type}`;
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('show'), 4000);
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Başlat ───────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', initApp);
