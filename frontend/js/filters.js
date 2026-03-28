/* ── filters.js ──────────────────────────────────────────────────
   Filtre aksiyonları - app.js'deki fonksiyonlara köprü.
   Tüm ağır iş app.js'de, burada sadece event helper'lar var.
──────────────────────────────────────────────────────────────── */

// Tarih inputu için bugünü maksimum tarih olarak ayarla
document.addEventListener('DOMContentLoaded', () => {
  const today = new Date().toISOString().split('T')[0];
  const dateFrom = document.getElementById('dateFrom');
  const dateTo   = document.getElementById('dateTo');
  if (dateFrom) dateFrom.max = today;
  if (dateTo)   dateTo.max   = today;

  // dateFrom değişince dateTo minimum'u güncelle
  if (dateFrom) {
    dateFrom.addEventListener('change', () => {
      if (dateTo) dateTo.min = dateFrom.value;
    });
  }
});
