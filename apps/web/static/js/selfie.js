// Selfie dal vivo: si scatta con la fotocamera, non si carica dalla galleria. Il file finisce nel campo nascosto del modulo.
(function () {
  const box = document.getElementById('selfie-box');
  if (!box) return;
  const video = document.getElementById('selfie-video'), canvas = document.getElementById('selfie-canvas'), img = document.getElementById('selfie-anteprima');
  const apri = document.getElementById('selfie-apri'), scatta = document.getElementById('selfie-scatta'), rifai = document.getElementById('selfie-rifai');
  const stato = document.getElementById('selfie-stato'), input = box.querySelector('input[type=file]');
  let flusso = null;
  const ferma = () => { if (flusso) flusso.getTracks().forEach(t => t.stop()); flusso = null; video.hidden = true; };
  async function avvia() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { stato.textContent = 'Questo dispositivo o browser non permette di usare la fotocamera: non è possibile completare la verifica da qui.'; return; }
    try {
      flusso = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 } }, audio: false });
      video.srcObject = flusso; video.hidden = false; await video.play();
      apri.hidden = true; scatta.hidden = false; rifai.hidden = true; img.hidden = true; stato.textContent = 'Inquadra il viso e premi «Scatta».';
    } catch (e) { stato.textContent = 'Non riesco ad aprire la fotocamera: consenti l\'accesso nelle impostazioni del browser e riprova.'; }
  }
  apri.addEventListener('click', avvia); rifai.addEventListener('click', avvia);
  scatta.addEventListener('click', () => {
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    canvas.toBlob(blob => {
      const dt = new DataTransfer(); dt.items.add(new File([blob], 'selfie.jpg', { type: 'image/jpeg' })); input.files = dt.files;
      img.src = URL.createObjectURL(blob); img.hidden = false; ferma(); scatta.hidden = true; rifai.hidden = false;
      stato.textContent = 'Selfie scattato. Se non ti convince puoi rifarlo.';
    }, 'image/jpeg', 0.88);
  });
  input.form.addEventListener('submit', e => {
    if (!input.files.length) { e.preventDefault(); stato.textContent = 'Scatta il selfie con la fotocamera prima di continuare.'; box.scrollIntoView({ block: 'center' }); }
  });
  window.addEventListener('pagehide', ferma);
})();
