// Mappa delle segnalazioni pubbliche (Leaflet + OpenStreetMap), con raggruppamento dei segnaposto vicini.
(function () {
  const el = document.getElementById('mappa');
  if (!el || typeof L === 'undefined') return;
  const mappa = L.map(el, { zoomControl: true, scrollWheelZoom: true }).setView([45.4642, 9.19], 12);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(mappa);

  const icona = tipo => L.divIcon({ className: 'pin-contenitore', html: `<span class="pin pin-${tipo}"></span>`, iconSize: [30, 38], iconAnchor: [15, 36], popupAnchor: [0, -32] });
  const gruppo = typeof L.markerClusterGroup === 'function'
    ? L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 48,
        iconCreateFunction: c => L.divIcon({ className: 'pin-contenitore', html: `<span class="grappolo">${c.getChildCount()}</span>`, iconSize: [42, 42] }) })
    : L.layerGroup();
  gruppo.addTo(mappa);

  const legenda = L.control({ position: 'bottomleft' });
  legenda.onAdd = () => {
    const d = L.DomUtil.create('div', 'legenda-mappa');
    d.innerHTML = '<span><i class="pin-mini pin-problema"></i> Problema</span><span><i class="pin-mini pin-proposta"></i> Proposta</span>';
    return d;
  };
  legenda.addTo(mappa);

  fetch(el.dataset.url).then(r => r.json()).then(dati => {
    const punti = [];
    dati.features.forEach(f => {
      const p = f.properties, ll = [f.geometry.coordinates[1], f.geometry.coordinates[0]];
      const m = L.marker(ll, { icon: icona(p.tipo), title: p.titolo, keyboard: true, alt: p.titolo });
      const d = document.createElement('div'); d.className = 'popup-segnalazione';
      const tag = document.createElement('span'); tag.className = 'popup-tag popup-' + p.tipo; tag.textContent = (p.tipo === 'proposta' ? 'Proposta' : 'Problema') + ' · ' + p.stato;
      const a = document.createElement('a'); a.href = p.url; a.textContent = p.titolo;
      const info = document.createElement('div'); info.className = 'popup-info';
      info.textContent = p.quartiere + ' · ' + p.sostegni + (p.sostegni === 1 ? ' sostegno' : ' sostegni');
      d.append(tag, a, info);
      m.bindPopup(d, { minWidth: 200, maxWidth: 280 });
      gruppo.addLayer(m); punti.push(ll);
    });
    if (punti.length) mappa.fitBounds(L.latLngBounds(punti), { padding: [40, 40], maxZoom: 15 });
    const n = document.getElementById('mappa-conteggio');
    if (n) n.textContent = punti.length + ' segnalazioni sulla mappa';
  });
})();
