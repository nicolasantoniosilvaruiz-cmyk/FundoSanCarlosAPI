document.querySelectorAll('[data-preset]').forEach(button => {
  button.addEventListener('click', () => { document.querySelector('#id_porcentaje').value = button.dataset.preset; });
});
const config = document.querySelector('#levels-config');
if (config) {
  const formatter = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 });
  const time = value => value ? new Intl.DateTimeFormat('es-CL', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date(value)) : 'Sin lecturas';
  const status = document.querySelector('#network-status');
  const refresh = document.querySelector('#refresh-levels');
  let busy = false;
  function paint(items) {
    items.forEach(e => {
      const card = document.querySelector(`[data-tank="${e.id}"]`);
      if (!card) return;
      card.querySelector('[data-pct]').innerHTML = `${e.porcentaje === null ? '—' : formatter.format(e.porcentaje)}<span>%</span>`;
      card.querySelector('[data-volume]').innerHTML = `${e.volumen === null ? '—' : formatter.format(e.volumen)} <small>L</small>`;
      card.querySelector('[data-capacity]').textContent = `${formatter.format(e.capacidad)} L`;
      card.querySelector('.gauge').style.setProperty('--level', `${e.porcentaje ?? 0}%`);
      card.querySelector('.gauge').setAttribute('aria-label', `Nivel: ${e.porcentaje ?? 'sin datos'} por ciento`);
      card.querySelector('[data-date]').textContent = time(e.fecha);
      const badge = card.querySelector('[data-status]');
      badge.textContent = e.volumen === null ? 'Sin mediciones' : e.bajo ? 'Nivel bajo' : 'Nivel disponible';
      badge.className = `pill ${e.bajo ? 'danger' : e.volumen === null ? 'neutral' : 'good'}`;
      const fresh = card.querySelector('[data-freshness]');
      fresh.textContent = e.desactualizado ? '● Lectura desactualizada' : '● Lectura reciente';
      fresh.classList.toggle('stale', e.desactualizado);
      if (e.tipo === 'agua') {
        const threshold = card.querySelector('[data-threshold]');
        if (threshold) threshold.textContent = `${formatter.format(e.umbral)} %`;
        document.querySelector('#low-water-banner').classList.toggle('hidden', !e.bajo);
      }
    });
  }
  paint(JSON.parse(document.querySelector('#initial-levels').textContent));
  async function update() {
    if (busy) return;
    busy = true; refresh.disabled = true;
    try {
      const response = await fetch(config.dataset.url, {headers:{'Accept':'application/json'}, cache:'no-store'});
      if (response.redirected) { window.location.assign(response.url); return; }
      if (!response.ok) throw new Error('No disponible');
      paint((await response.json()).estanques);
      status.textContent = '● Servidor disponible'; status.classList.remove('disconnected');
    } catch {
      status.textContent = '● Sin conexión al servidor · última información recibida';
      status.classList.add('disconnected');
    } finally {busy = false; refresh.disabled = false;}
  }
  refresh.addEventListener('click', update);
  setInterval(update, 15000);
  window.addEventListener('online', update);
}
