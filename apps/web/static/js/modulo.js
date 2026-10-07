// Aiuti del modulo «Nuova segnalazione»: contatori di caratteri e anteprima dei file scelti.
(function () {
  const conta = (campo, min, max) => {
    if (!campo) return;
    const p = document.createElement('p'); p.className = 'conta';
    const a = document.createElement('span'), b = document.createElement('span');
    p.append(a, b); campo.insertAdjacentElement('afterend', p);
    const agg = () => {
      const n = campo.value.length;
      b.textContent = n + ' / ' + max; b.className = n > max ? 'troppo' : '';
      a.textContent = n < min ? 'Ancora ' + (min - n) + ' caratteri per arrivare al minimo' : '';
    };
    campo.addEventListener('input', agg); agg();
  };
  conta(document.getElementById('id_titolo'), 0, 100);
  conta(document.getElementById('id_descrizione'), 30, 2000);

  const input = document.getElementById('media');
  if (!input) return;
  const lista = document.createElement('ul'); lista.className = 'anteprime'; lista.setAttribute('aria-label', 'File scelti');
  input.insertAdjacentElement('afterend', lista);
  const MB = 1024 * 1024;
  input.addEventListener('change', () => {
    lista.querySelectorAll('img').forEach(i => URL.revokeObjectURL(i.src));
    lista.replaceChildren();
    [...input.files].forEach(f => {
      const li = document.createElement('li');
      const video = f.type.startsWith('video/');
      if (video) { const d = document.createElement('div'); d.className = 'video-segnaposto'; d.textContent = 'VIDEO'; li.append(d); }
      else if (f.type.startsWith('image/') && f.type !== 'image/heic') { const i = document.createElement('img'); i.alt = ''; i.src = URL.createObjectURL(f); li.append(i); }
      const nome = document.createElement('span'); nome.textContent = f.name + ' · ' + (f.size / MB).toFixed(1) + ' MB'; li.append(nome);
      const max = video ? 50 * MB : 10 * MB;
      if (f.size > max) { const e = document.createElement('span'); e.className = 'problema'; e.textContent = 'Troppo grande (massimo ' + (video ? 50 : 10) + ' MB)'; li.append(e); }
      lista.append(li);
    });
    if (input.files.length > 10) { const li = document.createElement('li'); li.innerHTML = ''; const e = document.createElement('span'); e.className = 'problema'; e.textContent = 'Massimo 10 file: ne hai scelti ' + input.files.length; li.append(e); lista.append(li); }
  });
})();
