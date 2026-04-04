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
  onlyMultiSource: false,
  mapReady: false,
};

// Kategori renk paleti
const CATEGORY_COLORS = {
  'Trafik Kazasi':        { color: '#da3131', icon: '🚗', label: 'Trafik Kazası' },
  'Yangin':               { color: '#e8762b', icon: '🔥', label: 'Yangın' },
  'Elektrik Kesintisi':   { color: '#d4b700', icon: '⚡', label: 'Elektrik Kesintisi' },
  'Hirsizlik':            { color: '#5c6bc0', icon: '🔒', label: 'Hırsızlık' },
  'Suc ve Cinayet':       { color: '#9c27b0', icon: '⚖️', label: 'Suç ve Cinayet' },
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

    // Varsayilan tarih: son 3 gun
    const d = new Date();
    d.setDate(d.getDate() - 3);
    const defaultFrom = d.toISOString().slice(0, 10);
    state.dateFrom = defaultFrom;
    const dateFromEl = document.getElementById('dateFrom');
    if (dateFromEl) dateFromEl.value = defaultFrom;

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
    
    // UI lokal filtre: Sadece Duplicate (Çoklu Kaynak) Habere sahip olanlari listele
    if (state.onlyMultiSource) {
      state.filtered = state.allNews.filter(n => n.sources && n.sources.length > 1);
    } else {
      state.filtered = state.allNews;
    }

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
  state.onlyMultiSource = document.getElementById('onlyMultiSource').checked;
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
  
  const multisrc = document.getElementById('onlyMultiSource');
  if (multisrc) multisrc.checked = false;
  state.onlyMultiSource = false;
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

    const bar = document.getElementById('sourceStatsBar');
    const bySource = data.data.by_source || {};
    const entries = Object.entries(bySource).sort((a, b) => b[1] - a[1]);
    if (entries.length) {
      bar.innerHTML =
        '<span class="source-stats-label">Kaynaklara Göre:</span>' +
        entries.map(([name, count]) =>
          `<span class="source-stat">${escHtml(name)} <span class="src-count">${count}</span></span>`
        ).join('');
    } else {
      bar.innerHTML = '';
    }
  } catch (err) {}
}

// ── Scraping Tetikle ──────────────────────────────────────────
async function triggerScrape() {
  const btn = document.getElementById('btnScrape');
  const label = document.getElementById('scrapeLabel');
  if (btn.classList.contains('loading')) return;

  btn.classList.add('loading');
  label.textContent = 'Kazınıyor...';
  showToast('Veritabanı temizleniyor ve haberler yeniden kazınıyor...', 'info');

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
    showToast(err.message || 'Scraping başlatılamadı.', 'error');
  }
}

function pollScrapeStatus() {
  const label = document.getElementById('scrapeLabel');
  const btn = document.getElementById('btnScrape');
  const maxTicks = 800;
  let ticks = 0;
  const interval = setInterval(async () => {
    ticks += 1;
    try {
      const data = await fetchJSON(`${API_BASE}/scrape/status`);
      const prog = data.data.progress || {};
      if (prog.message && label) {
        const short = prog.message.length > 52 ? prog.message.slice(0, 50) + '…' : prog.message;
        label.textContent = short;
      }
      if (!data.data.running) {
        clearInterval(interval);
        btn.classList.remove('loading');
        label.textContent = 'Haberleri Güncelle';
        const stats = data.data.last_stats || {};
        if (stats.error) {
          showToast(`Scraping hata: ${stats.error}`, 'error');
        } else {
          const m = stats.db_merged != null ? `, ${stats.db_merged} çift kayıt birleştirildi` : '';
          showToast(`Tamamlandı. ${stats.saved ?? 0} yeni kayıt, ${stats.duplicate ?? 0} anında birleşen${m}.`, 'success');
        }
        await loadNews();
      } else if (ticks >= maxTicks) {
        clearInterval(interval);
        btn.classList.remove('loading');
        label.textContent = 'Haberleri Güncelle';
        showToast(
          'Çok uzun sürdü veya sunucu yanıt vermiyor. Flask konsoluna bakın; işlem arka planda sürebilir.',
          'error'
        );
      }
    } catch (err) {
      clearInterval(interval);
      btn.classList.remove('loading');
      if (label) label.textContent = 'Haberleri Güncelle';
      showToast('Durum alınamadı. Backend çalışıyor mu?', 'error');
      console.error(err);
    }
  }, 2500);
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
    const catInfo = CATEGORY_COLORS[cat] || { icon: '📰', label: cat || 'Haber' };
    const hasLoc = n.location && n.location.lat;
    const locHint = hasLoc ? 'Haritada gösteriliyor' : 'Konum yok / haritada yok';
    const dateStr = n.published_at ? new Date(n.published_at).toLocaleDateString('tr-TR') : '—';
    const catClass = cat.replace(/\s+/g, '-');
    // Ayni haber: tum sitelerin linkleri (URL bazli tekil; farkli sitelerin hepsi gorunsun)
    const seenUrls = new Set();
    const seenSourceNames = new Set();
    const linkRows = [];
    if (Array.isArray(n.sources)) {
      for (const s of n.sources) {
        const u = (s && s.url) ? String(s.url).trim() : '';
        const name = (s && s.source_name) ? s.source_name : 'Kaynak';
        if (!u || seenUrls.has(u) || seenSourceNames.has(name)) continue;
        seenUrls.add(u);
        seenSourceNames.add(name);
        linkRows.push({ url: u, name });
      }
    }
    const mainU = (n.url || '').trim();
    if (mainU && !seenUrls.has(mainU)) {
      const nm = (n.sources && n.sources[0] && n.sources[0].source_name) ? n.sources[0].source_name : 'Haber';
      if (!seenSourceNames.has(nm)) {
        seenUrls.add(mainU);
        seenSourceNames.add(nm);
        linkRows.unshift({ url: mainU, name: nm });
      }
    }
    const srcCount = linkRows.length;
    const multiBadge = srcCount > 1
      ? `<span style="font-size:0.7rem;margin-left:6px;padding:2px 6px;border-radius:4px;background:#238636;color:#fff;">${srcCount} kaynak</span>`
      : '';
    let multiLinksHTML = linkRows.length
      ? linkRows.map(s =>
          `<a href="${encodeURI(s.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()" style="font-size:0.75rem; color:#58a6ff; text-decoration:none; margin-right:8px; display:inline-block; margin-top:5px; border:1px solid #30363d; padding:2px 6px; border-radius:4px; background:#21262d;">${escHtml(s.name)} ↗</a>`
        ).join(' ')
      : '';

    return `
      <div class="news-card" data-cat="${cat}" data-id="${n._id}"
           onclick="onCardClick('${n._id}', ${hasLoc ? n.location.lat : 'null'}, ${hasLoc ? n.location.lng : 'null'})">
        <div class="card-meta">
          <span class="cat-badge ${catClass}">${catInfo.icon} ${catInfo.label}</span>
          <span class="card-date">${dateStr}</span>
        </div>
        <div class="card-title">${escHtml(n.title)}${multiBadge}</div>
        <div class="card-source" style="margin-bottom: 2px;">
          <span class="card-loc-icon">${hasLoc ? '📍' : '📌'}</span>
          <span style="font-size: 0.8rem; color: #8b949e;">${locHint}</span>
        </div>
        <div class="card-links" style="border-top: 1px solid #30363d; padding-top: 4px;">
          ${multiLinksHTML}
        </div>
      </div>`;
  }).join('');

  document.getElementById('newsCount').textContent = newsList.length;
}

function onCardClick(id, lat, lng) {
  if (lat && lng && state.mapReady) {
    panToMarker(id, lat, lng);
  }
  const news = state.allNews.find(n => n._id === id);
  if (news) openDetailPanel(news);
}

function openDetailPanel(news) {
  const panel = document.getElementById('newsDetailPanel');
  const container = document.getElementById('detailContent');
  const cat = news.category || '';
  const catInfo = CATEGORY_COLORS[cat] || { color: '#8b949e', icon: '📰', label: cat || 'Haber' };
  const dateStr = news.published_at
    ? new Date(news.published_at).toLocaleDateString('tr-TR', { year:'numeric', month:'long', day:'numeric', hour:'2-digit', minute:'2-digit' })
    : '';
  const locText = (news.location && news.location.text) ? news.location.text : '';
  const summary = news.summary || '';

  const sourceLinks = (news.sources || []).map(s =>
    `<a href="${encodeURI(s.url)}" target="_blank" rel="noopener" class="detail-source-link" onclick="event.stopPropagation()">${escHtml(s.source_name)} ↗</a>`
  ).join('');

  const mainUrl = (news.sources && news.sources.length) ? news.sources[0].url : (news.url || '#');

  container.innerHTML = `
    <div class="detail-cat-badge" style="background:${catInfo.color}22;color:${catInfo.color};border:1px solid ${catInfo.color}44;">
      ${catInfo.icon} ${catInfo.label}
    </div>
    <div class="detail-title">${escHtml(news.title)}</div>
    ${dateStr ? `<div class="detail-meta">📅 ${dateStr}</div>` : ''}
    ${locText ? `<div class="detail-meta">📍 ${escHtml(locText)}</div>` : ''}
    
    ${summary ? `
      <div class="detail-summary">
        <div class="detail-summary-label">Haber Özeti</div>
        ${escHtml(summary)}
      </div>` : `
      <div class="detail-summary" style="color:#6e7681;font-size:.82rem;padding:10px 12px;background:#161b2288;border-radius:8px;border-left:3px solid #30363d;">
        Bu haberin özeti oluşturulamadı. Detaylar için aşağıdaki kaynağa göz atın.
      </div>`}
    <div class="detail-sources">
      <div class="detail-summary-label" style="margin-bottom:.3rem;">Kaynaklar</div>
      ${sourceLinks}
    </div>
    <a href="${encodeURI(mainUrl)}" target="_blank" rel="noopener" class="detail-go-btn">Haberin Tamamını Oku →</a>
  `;
  panel.classList.add('open');
}

function closeDetailPanel() {
  document.getElementById('newsDetailPanel').classList.remove('open');
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
