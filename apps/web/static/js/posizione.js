// Scelta del luogo (mappa, indirizzo, GPS) e suggerimento delle categorie nel modulo "Nuova segnalazione".
(function () {
  const el = document.getElementById('mappa-scelta');
  if (!el || typeof L === 'undefined') return;
  const lat = document.getElementById('id_latitudine'), lon = document.getElementById('id_longitudine');
  const esito = document.getElementById('esito-posizione');
  const mappa = L.map(el).setView([45.4642, 9.19], 12);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(mappa);
  let segnaposto = null;

  async function imposta(la, lo, centra) {
    lat.value = la.toFixed(6); lon.value = lo.toFixed(6);
    pianificaSimili();
    if (!segnaposto) {
      segnaposto = L.marker([la, lo], { draggable: true }).addTo(mappa);
      segnaposto.on('dragend', () => { const p = segnaposto.getLatLng(); imposta(p.lat, p.lng, false); });
    } else segnaposto.setLatLng([la, lo]);
    if (centra) mappa.setView([la, lo], 16);
    try {
      const r = await (await fetch(`${window.URL_QUARTIERE}?lat=${la}&lon=${lo}`)).json();
      esito.textContent = r.dentro_milano ? `Luogo scelto: quartiere ${r.quartiere}.` : 'Questo punto è fuori dal Comune di Milano: sposta il segnaposto.';
    } catch { esito.textContent = 'Luogo scelto.'; }
  }
  if (lat.value && lon.value) imposta(parseFloat(lat.value), parseFloat(lon.value), true);
  mappa.on('click', e => imposta(e.latlng.lat, e.latlng.lng, false));

  document.getElementById('usa-posizione').addEventListener('click', () => {
    if (!navigator.geolocation) { esito.textContent = 'Il tuo browser non supporta la geolocalizzazione.'; return; }
    esito.textContent = 'Cerco la tua posizione…';
    navigator.geolocation.getCurrentPosition(p => imposta(p.coords.latitude, p.coords.longitude, true),
      () => { esito.textContent = 'Non riesco a leggere la posizione: autorizza il browser o usa la mappa.'; });
  });
  async function cerca() {
    const q = document.getElementById('cerca-indirizzo').value.trim();
    if (!q) return;
    esito.textContent = 'Cerco l\'indirizzo…';
    const url = 'https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=it&viewbox=9.04,45.54,9.28,45.38&bounded=1&q=' + encodeURIComponent(q + ', Milano');
    try {
      const r = await (await fetch(url, { headers: { 'Accept-Language': 'it' } })).json();
      if (r.length) imposta(parseFloat(r[0].lat), parseFloat(r[0].lon), true);
      else esito.textContent = 'Indirizzo non trovato: prova con la mappa.';
    } catch { esito.textContent = 'La ricerca dell\'indirizzo non è disponibile: usa la mappa.'; }
  }
  document.getElementById('vai-indirizzo').addEventListener('click', cerca);
  document.getElementById('cerca-indirizzo').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); cerca(); } });

  // Suggerimento delle categorie (simulato) dal testo
  const titolo = document.getElementById('id_titolo'), descr = document.getElementById('id_descrizione');
  let t;
  async function suggerisci() {
    if (descr.value.length < 20) return;
    const r = await (await fetch(`${window.URL_SUGGERISCI}?titolo=${encodeURIComponent(titolo.value)}&descrizione=${encodeURIComponent(descr.value)}`)).json();
    const nomi = [];
    document.querySelectorAll('input[name="categorie"]').forEach(c => {
      const s = r.categorie.find(x => String(x.id) === c.value);
      if (s && !c.dataset.scelta) { c.checked = true; }
      if (s) nomi.push(`${s.nome} (${Math.round(s.confidenza * 100)}%)`);
    });
    document.getElementById('suggerimento').textContent = nomi.length ? 'Suggerite: ' + nomi.join(', ') + '.' : '';
  }
  [titolo, descr].forEach(x => x.addEventListener('input', () => { clearTimeout(t); t = setTimeout(suggerisci, 700); }));
  document.querySelectorAll('input[name="categorie"]').forEach(c => c.addEventListener('change', () => { c.dataset.scelta = '1'; }));
  // Segnalazioni simili in zona (par. 5.3): si cercano quando cambiano posizione, testo o categorie
  const pannello = document.getElementById('simili'), elenco = document.getElementById('elenco-simili');
  const token = () => (document.querySelector('input[name=csrfmiddlewaretoken]') || {}).value;
  var ts; // var: la funzione può partire (in modifica) prima di questa riga
  function pianificaSimili() { clearTimeout(ts); ts = setTimeout(cercaSimili, 900); }
  function riga(x, puo) {
    const li = document.createElement('li');
    const a = document.createElement('a'); a.href = x.url; a.target = '_blank'; a.rel = 'noopener'; a.textContent = x.titolo;
    a.style.fontWeight = '700';
    const info = document.createElement('div'); info.className = 'piccolo';
    const scrivi = () => { info.textContent = `${x.quartiere} · a ${x.distanza_m} m · ${x.stato} · ${x.sostegni} sostegni · ${x.commenti} commenti`; };
    scrivi();
    li.append(a, info);
    if (puo && !x.propria) {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'btn btn-lieve btn-piccolo';
      const testo = () => { b.textContent = x.sostenuta ? 'Sostenuta · ritira' : 'Sostieni questa'; b.setAttribute('aria-pressed', String(x.sostenuta)); };
      testo();
      b.addEventListener('click', async () => {
        b.disabled = true;
        try {
          const r = await fetch(`/api/segnalazioni/${x.id}/sostieni/`, { method: 'POST', headers: { 'X-CSRFToken': token() } });
          const j = await r.json();
          if (r.ok) { x.sostenuta = j.sostenuta; x.sostegni = j.sostegni; scrivi(); testo(); }
          else { info.textContent = j.errore || 'Non è stato possibile registrare il sostegno.'; }
        } catch { info.textContent = 'Connessione non riuscita: riprova.'; }
        b.disabled = false;
      });
      li.append(b);
    }
    return li;
  }
  async function cercaSimili() {
    if (!pannello || !lat.value || !lon.value) return;
    const cat = [...document.querySelectorAll('input[name="categorie"]:checked')].map(c => c.value).join(',');
    const p = new URLSearchParams({ lat: lat.value, lon: lon.value, titolo: titolo.value, descrizione: descr.value, categorie: cat });
    if (window.ESCLUDI_ID) p.set('escludi', window.ESCLUDI_ID);
    try {
      const j = await (await fetch(`${window.URL_SIMILI}?${p}`)).json();
      elenco.replaceChildren(...j.simili.map(x => riga(x, j.puo_sostenere)));
      pannello.hidden = j.simili.length === 0;
    } catch { /* la ricerca è solo un aiuto: se non risponde si prosegue */ }
  }
  [titolo, descr].forEach(x => x.addEventListener('input', pianificaSimili));
  document.querySelectorAll('input[name="categorie"]').forEach(c => c.addEventListener('change', pianificaSimili));
  if (lat.value && lon.value) pianificaSimili();
})();
