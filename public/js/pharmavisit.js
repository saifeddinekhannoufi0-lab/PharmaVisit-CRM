/**
 * PharmaVisit CRM — Frontend Application
 *
 * Architecture: pure vanilla JS SPA, no framework.
 * Auth: Sanctum bearer token stored in localStorage.
 * All state lives in the `State` object.
 */

// ─── State ────────────────────────────────────────────────────────────────────
const State = {
  token:       null,
  user:        null,
  territory:   null,
  doctors:     [],
  pharmacies:  [],
  selectedIds: new Set(),
  activeTab:   'doctors',
  currentRoute: null,
  markers:     [],
  routeLayer:  null,
  map:         null,
  activePanel: null,   // doctor currently in visit panel
};

// ─── API helper ───────────────────────────────────────────────────────────────
async function api(method, path, body = null) {
  const opts = {
    method,
    headers: {
      'Accept':       'application/json',
      'Content-Type': 'application/json',
    },
  };
  if (State.token) opts.headers['Authorization'] = `Bearer ${State.token}`;
  if (body)        opts.body = JSON.stringify(body);

  const res = await fetch(`/api${path}`, opts);

  if (res.status === 401) {
    logout();
    return null;
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(data?.message || `HTTP ${res.status}`);
  return data;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
async function login() {
  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl    = document.getElementById('login-error');

  try {
    const data = await api('POST', '/auth/login', { email, password });
    if (!data) return;

    State.token = data.token;
    State.user  = data.user;
    localStorage.setItem('pharmavisit_token', data.token);

    document.getElementById('login-overlay').style.display = 'none';
    errEl.style.display = 'none';
    await initDashboard();
  } catch (e) {
    errEl.textContent = e.message || 'Invalid credentials';
    errEl.style.display = 'block';
  }
}

function logout() {
  api('POST', '/auth/logout').catch(() => {});
  localStorage.removeItem('pharmavisit_token');
  location.reload();
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────
async function bootstrap() {
  const savedToken = localStorage.getItem('pharmavisit_token');
  if (savedToken) {
    State.token = savedToken;
    try {
      State.user = await api('GET', '/auth/me');
      if (State.user) {
        document.getElementById('login-overlay').style.display = 'none';
        await initDashboard();
        return;
      }
    } catch {
      localStorage.removeItem('pharmavisit_token');
      State.token = null;
    }
  }

  // Show login
  document.getElementById('login-overlay').style.display = 'flex';
}

async function initDashboard() {
  renderRepCard();

  // Load territory + doctors + pharmacies in parallel
  const [territory, doctors, pharmacies] = await Promise.all([
    api('GET', '/territory'),
    api('GET', '/doctors?per_page=100'),
    api('GET', '/pharmacies?per_page=100'),
  ]);

  State.territory  = territory;
  State.doctors    = doctors?.data  ?? [];
  State.pharmacies = pharmacies?.data ?? [];

  renderStats();
  renderEntityList();

  // Drop all doctor pins on the map by default
  dropInitialPins();
}

// ─── Render rep card ──────────────────────────────────────────────────────────
function renderRepCard() {
  const u = State.user;
  document.getElementById('rep-name').textContent      = u.name;
  document.getElementById('rep-territory').textContent = u.territory?.name ?? '—';
  document.getElementById('rep-initials').textContent  =
    u.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}

// ─── Stats bar ────────────────────────────────────────────────────────────────
function renderStats() {
  const t = State.territory?.stats ?? {};
  document.getElementById('stat-doctors').textContent    = t.doctors    ?? State.doctors.length;
  document.getElementById('stat-pharmacies').textContent = t.pharmacies ?? State.pharmacies.length;
  document.getElementById('stat-reps').textContent       = t.reps       ?? '—';
}

// ─── Entity list ──────────────────────────────────────────────────────────────
function renderEntityList(filter = '') {
  const list    = document.getElementById('entity-list');
  const entities = State.activeTab === 'doctors' ? State.doctors : State.pharmacies;

  const filtered = filter
    ? entities.filter(e => {
        const name = (e.full_name ?? e.name ?? '').toLowerCase();
        const spec = (e.specialty ?? '').toLowerCase();
        const city = (e.city ?? '').toLowerCase();
        const q    = filter.toLowerCase();
        return name.includes(q) || spec.includes(q) || city.includes(q);
      })
    : entities;

  if (!filtered.length) {
    list.innerHTML = `<div class="empty-state"><div class="icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg></div><p>No results</p></div>`;
    return;
  }

  list.innerHTML = filtered.map(e => buildEntityCard(e)).join('');

  // Re-check selected state
  list.querySelectorAll('.entity-checkbox').forEach(cb => {
    cb.checked = State.selectedIds.has(parseInt(cb.dataset.id));
    cb.closest('.entity-item').classList.toggle('selected', cb.checked);
  });

  updateOptimizeButton();
}

function buildEntityCard(e) {
  const isDoc  = State.activeTab === 'doctors';
  const id     = e.id;
  const name   = isDoc ? e.full_name : e.name;
  const sub    = isDoc
    ? `${e.specialty} · ${e.city}`
    : `${e.manager_name ? e.manager_name + ' · ' : ''}${e.city}`;
  const prio   = e.priority ?? 'medium';
  const geocoded = e.is_geocoded;

  return `
    <div class="entity-item prio-${prio}" data-id="${id}" onclick="toggleSelect(${id}, this)">
      <input type="checkbox" class="entity-checkbox" data-id="${id}"
             onclick="event.stopPropagation(); toggleSelect(${id}, this.closest('.entity-item'))">
      <div class="entity-info">
        <div class="entity-name">${name}</div>
        <div class="entity-meta">${sub}</div>
      </div>
      ${isDoc ? `<span class="prio-badge ${prio}">${prio}</span>` : ''}
      <div class="geo-dot ${geocoded ? 'ok' : 'miss'}" title="${geocoded ? 'Geocoded' : 'No coordinates yet'}"></div>
    </div>`;
}

function toggleSelect(id, itemEl) {
  if (State.selectedIds.has(id)) {
    State.selectedIds.delete(id);
    itemEl.classList.remove('selected');
    itemEl.querySelector('.entity-checkbox').checked = false;
  } else {
    State.selectedIds.add(id);
    itemEl.classList.add('selected');
    itemEl.querySelector('.entity-checkbox').checked = true;
  }
  updateOptimizeButton();
}

function updateOptimizeButton() {
  const btn  = document.getElementById('btn-optimize');
  const info = document.getElementById('selection-info');
  const n    = State.selectedIds.size;
  btn.disabled = n < 1;
  info.textContent = n === 0
    ? 'Select doctors to plan your route'
    : `${n} stop${n > 1 ? 's' : ''} selected`;
}

// ─── Tab switching ────────────────────────────────────────────────────────────
function switchTab(tab) {
  State.activeTab = tab;
  State.selectedIds.clear();
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('search-input').value = '';
  renderEntityList();
}

// ─── Map ──────────────────────────────────────────────────────────────────────
function initMap() {
  State.map = L.map('map', {
    zoomControl: true,
    attributionControl: true,
  }).setView([33.97, -6.85], 12);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(State.map);
}

function dropInitialPins() {
  clearMapLayers();

  const entities = State.activeTab === 'doctors' ? State.doctors : State.pharmacies;
  entities.forEach(e => {
    if (!e.lat || !e.lng) return;

    const marker = L.marker([e.lat, e.lng], {
      icon: L.divIcon({
        className: '',
        html: `<div class="map-marker prio-${e.priority ?? 'medium'}" style="background:${prioColor(e.priority)}">
                 <span style="font-size:9px">+</span>
               </div>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      }),
    }).addTo(State.map);

    marker.on('click', () => showVisitPanel(e));
    State.markers.push(marker);
  });
}

function clearMapLayers() {
  State.markers.forEach(m => State.map.removeLayer(m));
  State.markers = [];
  if (State.routeLayer) {
    State.map.removeLayer(State.routeLayer);
    State.routeLayer = null;
  }
}

function prioColor(p) {
  return { high: '#f43f5e', medium: '#f59e0b', low: '#22c55e' }[p] ?? '#4f8ef7';
}

// ─── Optimization ─────────────────────────────────────────────────────────────
async function optimizeRoute() {
  if (State.selectedIds.size < 1) return;

  const btn = document.getElementById('btn-optimize');
  btn.classList.add('loading');
  showLoading('Optimizing your route…');

  try {
    const doctorIds = [...State.selectedIds];

    // Use map center as start, or compute average
    const center = State.map.getCenter();
    const result = await api('POST', '/routes/optimize', {
      doctor_ids: doctorIds,
      start_lat:  center.lat,
      start_lng:  center.lng,
      start_name: 'Your Location',
    });

    if (!result) return;

    State.currentRoute = result;
    renderOptimizedRoute(result);
    showToast(`Route optimized — ${result.ordered_stops.length} stops`, 'success');

  } catch (e) {
    showToast(`${e.message}`, 'error');
  } finally {
    btn.classList.remove('loading');
    hideLoading();
  }
}

function renderOptimizedRoute(result) {
  clearMapLayers();

  const stops = result.ordered_stops ?? [];

  // Start marker
  if (result.start_location) {
    const sl = result.start_location;
    const sm = L.marker([sl.lat, sl.lng], {
      icon: L.divIcon({
        className: '',
        html: `<div class="map-marker start"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg></div>`,
        iconSize: [34, 34], iconAnchor: [17, 17],
      }),
    }).addTo(State.map)
      .bindTooltip(`Start: ${sl.name}`, { permanent: false });
    State.markers.push(sm);
  }

  // Stop markers
  stops.forEach((stop, i) => {
    const m = L.marker([stop.lat, stop.lng], {
      icon: L.divIcon({
        className: '',
        html: `<div class="map-marker" style="background:${prioColor(stop.priority)}">${i + 1}</div>`,
        iconSize: [34, 34], iconAnchor: [17, 17],
      }),
    }).addTo(State.map);

    m.on('click', () => {
      // Find full doctor object
      const doctor = State.doctors.find(d => d.id === stop.id);
      showVisitPanel(doctor ?? stop);
    });

    State.markers.push(m);
  });

  // Route polyline from OSRM geometry
  if (result.geometry?.coordinates?.length > 1) {
    // GeoJSON coords are [lng, lat], Leaflet needs [lat, lng]
    const latLngs = result.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
    State.routeLayer = L.polyline(latLngs, {
      color: '#f97316',
      weight: 5,
      opacity: 0.85,
      lineJoin: 'round',
      lineCap: 'round',
    }).addTo(State.map);

    State.map.fitBounds(State.routeLayer.getBounds(), { padding: [40, 40] });
  } else if (stops.length > 0) {
    // Fallback: fit to markers
    const group = L.featureGroup(State.markers);
    State.map.fitBounds(group.getBounds(), { padding: [40, 40] });
  }

  // Route summary card
  renderSummaryCard(result);
}

function renderSummaryCard(result) {
  const stops   = result.ordered_stops ?? [];
  const distKm  = result.total_distance_m ? (result.total_distance_m / 1000).toFixed(1) : '—';
  const durMin  = result.total_duration_s ? Math.round(result.total_duration_s / 60) : '—';
  const durStr  = typeof durMin === 'number'
    ? `${Math.floor(durMin / 60)}h ${durMin % 60}m`
    : '—';

  const stopsMini = stops.slice(0, 6).map(s =>
    `<div class="stop-mini">
       <div class="stop-num">${s.stop_number}</div>
       <span>${s.name.replace('Dr. ', '')}</span>
     </div>`
  ).join('') + (stops.length > 6 ? `<div class="stop-mini" style="color:var(--text-muted)">+${stops.length - 6} more…</div>` : '');

  document.getElementById('route-summary').innerHTML = `
    <h3>Optimized Route</h3>
    <div class="summary-stats">
      <div class="summary-stat"><div class="val">${stops.length}</div><div class="lbl">Stops</div></div>
      <div class="summary-stat"><div class="val">${distKm}</div><div class="lbl">km</div></div>
      <div class="summary-stat"><div class="val">${durStr}</div><div class="lbl">Drive time</div></div>
    </div>
    <div class="stop-list-mini">${stopsMini}</div>
    ${result.notes ? `<p style="font-size:11px;color:var(--prio-med);margin-top:10px"><svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg> ${result.notes}</p>` : ''}
  `;

  document.getElementById('route-summary').classList.add('visible');
}

// ─── Visit log panel ──────────────────────────────────────────────────────────
function showVisitPanel(entity) {
  State.activePanel = entity;
  const isDoc = 'specialty' in entity;
  const name  = entity.full_name ?? entity.name;

  document.getElementById('visit-panel-name').textContent = name;
  document.getElementById('visit-panel-sub').textContent  = isDoc
    ? `${entity.specialty ?? ''} · ${entity.city ?? ''}`
    : entity.city ?? '';
  document.getElementById('visit-doctor-id').value    = isDoc ? entity.id : '';
  document.getElementById('visit-pharmacy-id').value  = isDoc ? '' : entity.id;
  document.getElementById('visit-notes').value        = '';
  document.getElementById('visit-duration').value     = '';
  document.getElementById('visit-outcome').value      = 'completed';

  document.getElementById('visit-panel').classList.add('open');
}

function closeVisitPanel() {
  document.getElementById('visit-panel').classList.remove('open');
  State.activePanel = null;
}

async function submitVisitLog() {
  const doctorId   = parseInt(document.getElementById('visit-doctor-id').value) || null;
  const pharmacyId = parseInt(document.getElementById('visit-pharmacy-id').value) || null;
  const notes      = document.getElementById('visit-notes').value.trim();
  const duration   = parseInt(document.getElementById('visit-duration').value) || null;
  const outcome    = document.getElementById('visit-outcome').value;

  try {
    await api('POST', '/visit-logs', {
      doctor_id:        doctorId,
      pharmacy_id:      pharmacyId,
      notes:            notes || null,
      duration_minutes: duration,
      outcome,
    });

    showToast('Visit logged successfully', 'success');
    closeVisitPanel();
  } catch (e) {
    showToast(`${e.message}`, 'error');
  }
}

// ─── Loading overlay ──────────────────────────────────────────────────────────
function showLoading(msg = 'Loading…') {
  document.getElementById('loading-text').textContent = msg;
  document.getElementById('loading-overlay').classList.add('visible');
}

function hideLoading() {
  document.getElementById('loading-overlay').classList.remove('visible');
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// ─── Search ───────────────────────────────────────────────────────────────────
let searchTimer = null;
function onSearch(val) {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => renderEntityList(val), 200);
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Map must be initialized here — Leaflet's L global is guaranteed ready after DOM parsing
  initMap();
  bootstrap();

  // Login form
  document.getElementById('btn-login').addEventListener('click', login);
  document.getElementById('login-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') login();
  });

  // Logout
  document.getElementById('btn-logout').addEventListener('click', logout);

  // Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Search
  document.getElementById('search-input').addEventListener('input', e => onSearch(e.target.value));

  // Optimize
  document.getElementById('btn-optimize').addEventListener('click', optimizeRoute);

  // Visit panel
  document.getElementById('btn-close-panel').addEventListener('click', closeVisitPanel);
  document.getElementById('btn-submit-visit').addEventListener('click', submitVisitLog);
});
