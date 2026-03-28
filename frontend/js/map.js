/* ── map.js ─────────────────────────────────────────────────────
   Google Maps entegrasyonu: marker'lar, InfoWindow, kamera
──────────────────────────────────────────────────────────────── */

let map = null;
let markers = {};         // { newsId: google.maps.Marker }
let activeInfoWindow = null;

// ── Google Maps'i Yükle ───────────────────────────────────────
function loadGoogleMaps(apiKey) {
  const script = document.getElementById('gmapsLoader');
  script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initMap&language=tr&region=TR`;
  script.async = true;
  script.defer = true;
}

// ── Haritayı Başlat (Google callback) ────────────────────────
window.initMap = function () {
  const center = window.KOCAELI_CENTER || { lat: 40.7654, lng: 29.9408 };

  map = new google.maps.Map(document.getElementById('map'), {
    center,
    zoom: 11,
    styles: DARK_MAP_STYLE,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: true,
    zoomControlOptions: {
      position: google.maps.ControlPosition.RIGHT_CENTER
    },
  });

  state.mapReady = true;

  // Harita hazırsa mevcut haberlere marker ekle
  if (state.filtered && state.filtered.length) {
    renderMarkers(state.filtered);
  }
};

// ── Marker'ları Çiz ───────────────────────────────────────────
function renderMarkers(newsList) {
  if (!map) return;

  // Önceki marker'ları temizle
  Object.values(markers).forEach(m => m.setMap(null));
  markers = {};

  if (activeInfoWindow) {
    activeInfoWindow.close();
    activeInfoWindow = null;
  }

  newsList.forEach(news => {
    if (!news.location || !news.location.lat || !news.location.lng) return;

    const cat = news.category || '';
    const info = CATEGORY_COLORS[cat] || { color: '#8b949e', icon: '📰', label: cat };
    const pos = { lat: news.location.lat, lng: news.location.lng };

    const marker = new google.maps.Marker({
      position: pos,
      map,
      title: news.title,
      icon: makeMarkerIcon(info.color, info.icon),
      animation: google.maps.Animation.DROP,
    });

    // InfoWindow içeriği
    const iw = buildInfoWindow(news, info);

    marker.addListener('click', () => {
      if (activeInfoWindow) activeInfoWindow.close();
      iw.open({ anchor: marker, map });
      activeInfoWindow = iw;
      // Hafif zoom & pan
      map.panTo(pos);
    });

    markers[news._id] = marker;
  });
}

// ── Marker Icon ───────────────────────────────────────────────
function makeMarkerIcon(color, emoji) {
  // SVG pin marker
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="36" height="46" viewBox="0 0 36 46">
      <defs>
        <filter id="sh" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#00000066"/>
        </filter>
      </defs>
      <path d="M18 0 C8 0 0 8 0 18 C0 30 18 46 18 46 C18 46 36 30 36 18 C36 8 28 0 18 0Z"
            fill="${color}" filter="url(#sh)"/>
      <circle cx="18" cy="18" r="10" fill="white" opacity="0.25"/>
      <text x="18" y="23" text-anchor="middle" font-size="13">${emoji}</text>
    </svg>`;

  return {
    url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
    scaledSize: new google.maps.Size(36, 46),
    anchor: new google.maps.Point(18, 46),
  };
}

// ── InfoWindow ────────────────────────────────────────────────
function buildInfoWindow(news, catInfo) {
  const dateStr = news.published_at
    ? new Date(news.published_at).toLocaleDateString('tr-TR', { year:'numeric', month:'long', day:'numeric' })
    : '—';

  const sourceLinks = (news.sources || []).map(s =>
    `<a href="${s.url}" target="_blank" rel="noopener" class="iw-source-link">${s.source_name}</a>`
  ).join(', ');

  const allSourceUrls = (news.sources && news.sources.length)
    ? news.sources[0].url
    : (news.url || '#');

  const content = `
    <div style="
      font-family:'Inter',sans-serif;
      background:#161b22;
      border-radius:10px;
      padding:14px;
      min-width:220px;
      max-width:290px;
      border:1px solid #30363d;
      box-shadow:0 8px 32px rgba(0,0,0,.6);
    ">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
        <span style="font-size:1.1rem">${catInfo.icon}</span>
        <span style="
          font-size:0.65rem;font-weight:700;
          background:${catInfo.color}22;color:${catInfo.color};
          border:1px solid ${catInfo.color}44;
          border-radius:10px;padding:2px 8px;
          text-transform:uppercase;letter-spacing:.05em;
        ">${catInfo.label}</span>
      </div>
      <div style="font-size:.82rem;font-weight:600;color:#e6edf3;line-height:1.4;margin-bottom:8px;">
        ${escHtml(news.title)}
      </div>
      <div style="font-size:.7rem;color:#8b949e;margin-bottom:4px;">📅 ${dateStr}</div>
      <div style="font-size:.7rem;color:#8b949e;margin-bottom:10px;">
        📰 ${sourceLinks || escHtml(news.source_name || '')}
      </div>
      ${news.location && news.location.text
        ? `<div style="font-size:.68rem;color:#8b949e;margin-bottom:10px;">📍 ${escHtml(news.location.text)}</div>`
        : ''}
      <a href="${allSourceUrls}" target="_blank" rel="noopener" style="
        display:block;text-align:center;
        background:linear-gradient(135deg,#1f6feb,#388bfd);
        color:#fff;font-size:.75rem;font-weight:600;
        padding:7px 14px;border-radius:7px;
        text-decoration:none;
        transition:opacity .2s;
      " onmouseover="this.style.opacity='.85'" onmouseout="this.style.opacity='1'">
        Habere Git →
      </a>
    </div>`;

  return new google.maps.InfoWindow({
    content,
    maxWidth: 300,
    disableAutoPan: false,
  });
}

// ── Karta tıklayınca haritada pan ────────────────────────────
function panToMarker(id, lat, lng) {
  if (!map) return;
  map.panTo({ lat, lng });
  map.setZoom(14);
  const m = markers[id];
  if (m) google.maps.event.trigger(m, 'click');
}

// ── Koyu Harita Stili ─────────────────────────────────────────
const DARK_MAP_STYLE = [
  { elementType:'geometry', stylers:[{ color:'#1a2233' }] },
  { elementType:'labels.text.stroke', stylers:[{ color:'#1a2233' }] },
  { elementType:'labels.text.fill', stylers:[{ color:'#8b949e' }] },
  { featureType:'administrative', elementType:'geometry.stroke', stylers:[{ color:'#30363d' }] },
  { featureType:'administrative.land_parcel', elementType:'labels.text.fill', stylers:[{ color:'#6e7681' }] },
  { featureType:'landscape.natural', elementType:'geometry', stylers:[{ color:'#161b22' }] },
  { featureType:'poi', elementType:'geometry', stylers:[{ color:'#21262d' }] },
  { featureType:'poi', elementType:'labels.text.fill', stylers:[{ color:'#6e7681' }] },
  { featureType:'poi.park', elementType:'geometry', stylers:[{ color:'#1e2d1e' }] },
  { featureType:'poi.park', elementType:'labels.text.fill', stylers:[{ color:'#3fb950' }] },
  { featureType:'road', elementType:'geometry', stylers:[{ color:'#2d3748' }] },
  { featureType:'road', elementType:'geometry.stroke', stylers:[{ color:'#1a2233' }] },
  { featureType:'road', elementType:'labels.text.fill', stylers:[{ color:'#8b949e' }] },
  { featureType:'road.highway', elementType:'geometry', stylers:[{ color:'#3d4f6e' }] },
  { featureType:'road.highway', elementType:'geometry.stroke', stylers:[{ color:'#1a2233' }] },
  { featureType:'road.highway', elementType:'labels.text.fill', stylers:[{ color:'#c9d1d9' }] },
  { featureType:'transit', elementType:'geometry', stylers:[{ color:'#21262d' }] },
  { featureType:'transit.station', elementType:'labels.text.fill', stylers:[{ color:'#8b949e' }] },
  { featureType:'water', elementType:'geometry', stylers:[{ color:'#0d2137' }] },
  { featureType:'water', elementType:'labels.text.fill', stylers:[{ color:'#58a6ff' }] },
  { featureType:'water', elementType:'labels.text.stroke', stylers:[{ color:'#0d1117' }] },
];
