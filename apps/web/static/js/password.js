// Campi password: pulsante «Mostra» accanto al campo; per le password nuove, aiuto in tempo reale che compare solo mentre si digita
// e mostra solo ciò che manca. Le regole sono le stesse di core/services/password.py; il server decide sempre.
(function () {
  const REGOLE = [
    ['Almeno 8 caratteri', p => p.length >= 8],
    ['Una lettera maiuscola', p => /[A-ZÀ-Ý]/.test(p)],
    ['Un numero', p => /\d/.test(p)],
    ['Un simbolo (per esempio ! ? % & # @ -)', p => /[^\w\s]|_/.test(p)],
  ];
  const troppoLunga = p => new TextEncoder().encode(p).length > 72;   // limite della cifratura, spiegato solo se superato

  document.querySelectorAll('input[type="password"]').forEach(campo => {
    if (campo.dataset.pwPronto) return;
    campo.dataset.pwPronto = '1';
    const riga = document.createElement('div'); riga.className = 'pw-riga';
    campo.parentNode.insertBefore(riga, campo); riga.append(campo);
    const mostra = document.createElement('button');
    mostra.type = 'button'; mostra.className = 'pw-mostra'; mostra.textContent = 'Mostra'; mostra.setAttribute('aria-pressed', 'false');
    mostra.setAttribute('aria-label', 'Mostra la password');
    mostra.addEventListener('click', () => {
      const visibile = campo.type === 'password';
      campo.type = visibile ? 'text' : 'password';
      mostra.textContent = visibile ? 'Nascondi' : 'Mostra'; mostra.setAttribute('aria-pressed', String(visibile));
      mostra.setAttribute('aria-label', visibile ? 'Nascondi la password' : 'Mostra la password');
    });
    riga.append(mostra);
    if (campo.dataset.password !== 'nuova') return;

    const aiuto = document.createElement('p');
    aiuto.className = 'pw-aiuto'; aiuto.setAttribute('aria-live', 'polite'); aiuto.hidden = true;
    riga.insertAdjacentElement('afterend', aiuto);
    const conferma = campo.form.querySelector('input[data-conferma]');
    const controllaConferma = () => { conferma.setCustomValidity(conferma.value && conferma.value !== campo.value ? 'Le due password non coincidono.' : ''); };
    const aggiorna = () => {
      const v = campo.value;
      if (!v) { aiuto.hidden = true; aiuto.textContent = ''; if (conferma) controllaConferma(); return; }
      const mancano = REGOLE.filter(([, ok]) => !ok(v)).map(([t]) => t.toLowerCase());
      aiuto.hidden = false;
      if (troppoLunga(v)) { aiuto.className = 'pw-aiuto no'; aiuto.textContent = 'Troppo lunga: al massimo 72 caratteri (le lettere accentate e le emoji ne contano di più).'; }
      else if (mancano.length) { aiuto.className = 'pw-aiuto no'; aiuto.textContent = 'Manca: ' + mancano.join(', ') + '.'; }
      else { aiuto.className = 'pw-aiuto ok'; aiuto.textContent = 'Password valida.'; }
      if (conferma) controllaConferma();
    };
    campo.addEventListener('input', aggiorna);
    if (conferma) conferma.addEventListener('input', controllaConferma);
    aggiorna();
  });
})();
