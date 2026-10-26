// Scelta del quartiere di Milano: dall'elenco (sempre disponibile) oppure da una mappa con i confini degli 88 quartieri (NIL).
(function () {
  const select = document.querySelector('select[data-mappa-quartiere]');
  if (!select || typeof L === 'undefined') return;
  const URL_CONTORNI = window.URL_CONTORNI, URL_QUARTIERE = window.URL_QUARTIERE;
  const pannello = document.createElement('div'); pannello.className = 'scelta-quartiere';
  const barra = document.createElement('div'); barra.className = 'scelta-barra';
  const bMappa = document.createElement('button'); bMappa.type = 'button'; bMappa.className = 'btn btn-lieve btn-piccolo'; bMappa.textContent = 'Scegli sulla mappa'; bMappa.setAttribute('aria-expanded', 'false');
  const bPos = document.createElement('button'); bPos.type = 'button'; bPos.className = 'btn btn-lieve btn-piccolo'; bPos.textContent = 'Usa la mia posizione';
  const stato = document.createElement('p'); stato.className = 'aiuto'; stato.setAttribute('role', 'status');
  const contenitore = document.createElement('div'); contenitore.className = 'mappa mappa-quartiere'; contenitore.hidden = true;
  contenitore.setAttribute('role', 'application'); contenitore.setAttribute('aria-label', 'Mappa dei quartieri di Milano: tocca un quartiere per sceglierlo');
  barra.append(bMappa, bPos); pannello.append(barra, stato, contenitore);
  select.parentNode.insertBefore(pannello, select.nextSibling);

  let mappa = null, livello = null, strati = {};
  const nomeScelto = () => select.selectedOptions[0] && select.value ? select.selectedOptions[0].textContent : '';
  const aggiornaStato = () => { stato.textContent = select.value ? 'Quartiere scelto: ' + nomeScelto() + '.' : 'Nessun quartiere scelto: puoi sceglierlo dall\'elenco o dalla mappa.'; };
  const stile = (scelto, sopra) => ({ color: '#101010', weight: scelto ? 3 : 1.2, fillColor: scelto ? '#e30613' : '#101010', fillOpacity: scelto ? .42 : (sopra ? .16 : .02) });
  function evidenzia() { Object.entries(strati).forEach(([id, l]) => l.setStyle(stile(String(id) === select.value, false))); }
  function imposta(id) { select.value = String(id); select.dispatchEvent(new Event('change', { bubbles: true })); }
  select.addEventListener('change', () => { aggiornaStato(); if (mappa) evidenzia(); });

  async function apri() {
    contenitore.hidden = false; bMappa.setAttribute('aria-expanded', 'true'); bMappa.textContent = 'Nascondi la mappa';
    if (!mappa) {
      mappa = L.map(contenitore, { gestureHandling: true, gestureHandlingOptions: { text: { touch: 'Usa due dita per muovere la mappa', scroll: 'Usa Ctrl + scorrimento per zoomare la mappa', scrollMac: 'Usa ⌘ + scorrimento per zoomare la mappa' } } });
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 17, referrerPolicy: 'origin', attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(mappa);
      try {
        const dati = await (await fetch(URL_CONTORNI)).json();
        livello = L.geoJSON(dati, {
          style: () => stile(false, false),
          onEachFeature: (f, l) => {
            strati[f.properties.id] = l;
            l.bindTooltip(f.properties.nome, { sticky: true });
            l.on('mouseover', () => { if (String(f.properties.id) !== select.value) l.setStyle(stile(false, true)); });
            l.on('mouseout', () => l.setStyle(stile(String(f.properties.id) === select.value, false)));
            l.on('click', () => imposta(f.properties.id));
          },
        }).addTo(mappa);
        const limiti = livello.getBounds();
        mappa.fitBounds(limiti); mappa.setMaxBounds(limiti.pad(0.25)); mappa.setMinZoom(mappa.getZoom() - 1);
        evidenzia();
      } catch { stato.textContent = 'Non riesco a caricare la mappa: scegli il quartiere dall\'elenco.'; }
    }
    setTimeout(() => mappa.invalidateSize(), 50);
  }
  bMappa.addEventListener('click', () => { if (contenitore.hidden) apri(); else { contenitore.hidden = true; bMappa.setAttribute('aria-expanded', 'false'); bMappa.textContent = 'Scegli sulla mappa'; } });
  bPos.addEventListener('click', () => {
    if (!navigator.geolocation) { stato.textContent = 'Il tuo browser non supporta la geolocalizzazione.'; return; }
    stato.textContent = 'Cerco la tua posizione…';
    navigator.geolocation.getCurrentPosition(async p => {
      try {
        const r = await (await fetch(`${URL_QUARTIERE}?lat=${p.coords.latitude}&lon=${p.coords.longitude}`)).json();
        if (r.dentro_milano) imposta(r.id); else stato.textContent = 'Sei fuori dal Comune di Milano: scegli un quartiere di Milano dall\'elenco o dalla mappa.';
      } catch { stato.textContent = 'Non riesco a leggere il quartiere dalla posizione.'; }
    }, () => { stato.textContent = 'Non riesco a leggere la posizione: autorizza il browser o scegli dall\'elenco.'; });
  });
  aggiornaStato();
})();
