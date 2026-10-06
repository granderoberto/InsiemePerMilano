// Mappa delle segnalazioni pubbliche (Leaflet + OpenStreetMap).
(function () {
  const el = document.getElementById('mappa');
  if (!el || typeof L === 'undefined') return;
  const mappa = L.map(el).setView([45.4642, 9.19], 12);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(mappa);
  fetch(el.dataset.url).then(r => r.json()).then(dati => {
    const livello = L.geoJSON(dati, {
      pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 8 + Math.min(10, f.properties.sostegni / 3), weight: 2, color: '#08425a',
        fillColor: f.properties.stato.startsWith('Presentata') ? '#a24a00' : '#0a5a78', fillOpacity: .85 }),
      onEachFeature: (f, layer) => {
        const p = f.properties, d = document.createElement('div');
        const a = document.createElement('a'); a.href = p.url; a.textContent = p.titolo; a.style.fontWeight = '700';
        const info = document.createElement('div'); info.textContent = p.quartiere + ' · ' + p.stato + ' · 👍 ' + p.sostegni;
        d.append(a, info); layer.bindPopup(d);
      } }).addTo(mappa);
    if (dati.features.length) mappa.fitBounds(livello.getBounds(), { padding: [30, 30], maxZoom: 15 });
  });
})();
