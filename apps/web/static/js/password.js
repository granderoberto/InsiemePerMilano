// Aiuto in tempo reale per le password nuove: requisiti spuntati, pulsante «Mostra», conferma uguale.
// Le regole sono le stesse di core/services/password.py; il server decide sempre (qui è solo un aiuto).
(function () {
  const REGOLE = [
    ['lunghezza', 'Almeno 8 caratteri', p => p.length >= 8],
    ['maiuscola', 'Una lettera maiuscola', p => /[A-ZÀ-Ý]/.test(p)],
    ['numero', 'Un numero', p => /\d/.test(p)],
    ['simbolo', 'Un simbolo (! ? % & # @ -)', p => /[^\w\s]|_/.test(p)],
    ['massimo', 'Al massimo 72 byte', p => new TextEncoder().encode(p).length <= 72],
  ];
  document.querySelectorAll('input[data-password="nuova"]').forEach(campo => {
    const lista = document.createElement('ul');
    lista.className = 'requisiti'; lista.setAttribute('aria-live', 'polite');
    const voci = REGOLE.map(([, testo]) => { const li = document.createElement('li'); li.textContent = testo; lista.append(li); return li; });
    const mostra = document.createElement('button');
    mostra.type = 'button'; mostra.className = 'btn btn-lieve btn-piccolo'; mostra.textContent = 'Mostra'; mostra.setAttribute('aria-pressed', 'false');
    mostra.addEventListener('click', () => {
      const visibile = campo.type === 'password';
      campo.type = visibile ? 'text' : 'password'; mostra.textContent = visibile ? 'Nascondi' : 'Mostra'; mostra.setAttribute('aria-pressed', String(visibile));
    });
    campo.insertAdjacentElement('afterend', lista); campo.insertAdjacentElement('afterend', mostra);
    const conferma = campo.form.querySelector('input[data-conferma]');
    const aggiorna = () => {
      REGOLE.forEach(([, , ok], i) => { const buono = ok(campo.value); voci[i].className = campo.value ? (buono ? 'ok' : 'no') : ''; voci[i].dataset.stato = buono ? '✓ ' : '✗ '; });
      if (conferma) controllaConferma();
    };
    const controllaConferma = () => { conferma.setCustomValidity(conferma.value && conferma.value !== campo.value ? 'Le due password non coincidono.' : ''); };
    campo.addEventListener('input', aggiorna);
    if (conferma) conferma.addEventListener('input', controllaConferma);
    aggiorna();
  });
})();
