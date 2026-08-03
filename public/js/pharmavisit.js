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
  activePanel: null,
  userLocation: null,        // { lat, lng, name, type, accuracy }
  locationMarker: null,      // Leaflet marker for user position
  _accuracyCircle: null,     // Leaflet circle for GPS accuracy radius
  _gpsWatchId: null,         // navigator.geolocation.watchPosition handle
  _clusterGroup: null,       // Leaflet.markercluster group
  settingStartLocation: false,
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

  // Load territory first, then fetch ALL doctors + pharmacies (paginated)
  const territory = await api('GET', '/territory');
  State.territory = territory;

  // Fetch all pages in parallel using per_page=500
  const [doctors, pharmacies] = await Promise.all([
    fetchAllPages('/doctors', 500),
    fetchAllPages('/pharmacies', 500),
  ]);

  State.doctors    = doctors;
  State.pharmacies = pharmacies;

  renderStats();
  renderEntityList();

  // Drop all doctor pins on the map by default
  dropInitialPins();

  // Proactively request user location on dashboard load
  requestUserLocation();
}

/**
 * Fetch all pages from a paginated API endpoint.
 * Returns a flat array of all items across all pages.
 */
async function fetchAllPages(endpoint, perPage = 500) {
  const firstPage = await api('GET', `${endpoint}?per_page=${perPage}&page=1`);
  if (!firstPage) return [];

  const items = [...(firstPage.data ?? [])];
  const lastPage = firstPage.last_page ?? 1;

  // Fetch remaining pages in parallel if there are more
  if (lastPage > 1) {
    const pageNums = Array.from({ length: lastPage - 1 }, (_, i) => i + 2);
    const pages = await Promise.all(
      pageNums.map(p => api('GET', `${endpoint}?per_page=${perPage}&page=${p}`))
    );
    for (const page of pages) {
      if (page?.data) items.push(...page.data);
    }
  }

  return items;
}

// ─── Render rep card ──────────────────────────────────────────────────────────
function renderRepCard() {
  const u = State.user;
  document.getElementById('rep-name').textContent      = u.name;
  document.getElementById('rep-territory').textContent = u.territory?.name ?? '—';
  const initialsEl = document.getElementById('rep-initials');
  if (initialsEl) {
    initialsEl.textContent = u.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  }
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
  const list     = document.getElementById('entity-list');
  const entities = State.activeTab === 'doctors' ? State.doctors : State.pharmacies;

  const q = filter.toLowerCase();
  const filtered = q
    ? entities.filter(e => {
        const name = (e.full_name ?? e.name ?? '').toLowerCase();
        const spec = (e.specialty ?? '').toLowerCase();
        const city = (e.city ?? '').toLowerCase();
        return name.includes(q) || spec.includes(q) || city.includes(q);
      })
    : entities;

  if (!filtered.length) {
    list.innerHTML = `<div class="empty-state"><div class="icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg></div><p>No results</p></div>`;
    return;
  }

  const isDocTab = State.activeTab === 'doctors';

  // Group by specialty / city
  const grouped = {};
  filtered.forEach(e => {
    const key = isDocTab ? (e.specialty || 'Unknown Specialty') : (e.city || 'Unknown City');
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(e);
  });

  const groups = Object.keys(grouped).sort();

  // Build HTML using DocumentFragment via a temp div for performance
  const frag = document.createDocumentFragment();
  const wrapper = document.createElement('div');

  // Expand only the first group; collapse all others by default
  groups.forEach((groupName, index) => {
    const catId    = `cat-${index}`;
    const isOpen   = index === 0 || !!q; // open first group, or all when searching
    const rotStyle = isOpen ? '' : 'transform:rotate(-90deg)';
    const dispStyle = isOpen ? 'block' : 'none';

    wrapper.innerHTML += `
      <div class="category-header" onclick="toggleCategory('${catId}')">
        <div>${groupName} <span class="cat-count">(${grouped[groupName].length})</span></div>
        <svg id="icon-${catId}" class="cat-chevron" style="${rotStyle}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
      </div>
      <div id="${catId}" style="display:${dispStyle}">
        ${grouped[groupName].map(e => buildEntityCard(e)).join('')}
      </div>`;
  });

  list.innerHTML = wrapper.innerHTML;

  // Restore checkbox states
  list.querySelectorAll('.entity-checkbox').forEach(cb => {
    cb.checked = State.selectedIds.has(parseInt(cb.dataset.id));
    cb.closest('.entity-item').classList.toggle('selected', cb.checked);
  });

  updateOptimizeButton();
}

window.toggleCategory = function(catId) {
  const el = document.getElementById(catId);
  const icon = document.getElementById(`icon-${catId}`);
  if (el.style.display === 'none') {
    el.style.display = 'block';
    if (icon) icon.style.transform = 'rotate(0deg)';
  } else {
    el.style.display = 'none';
    if (icon) icon.style.transform = 'rotate(-90deg)';
  }
};

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
    zoomControl: false,
    attributionControl: true,
  }).setView([33.97, -6.85], 12);

  L.control.zoom({ position: 'bottomright' }).addTo(State.map);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(State.map);
}

function dropInitialPins() {
  clearMapLayers();

  const entities = State.activeTab === 'doctors' ? State.doctors : State.pharmacies;
  const geocoded  = entities.filter(e => e.lat && e.lng);

  if (!geocoded.length) return;

  // Use marker clustering for performance with 600+ markers
  const cluster = L.markerClusterGroup({
    chunkedLoading: true,
    maxClusterRadius: 60,
    showCoverageOnHover: false,
    iconCreateFunction(c) {
      const n = c.getChildCount();
      const size = n < 10 ? 32 : n < 100 ? 40 : 48;
      return L.divIcon({
        html: `<div class="cluster-icon" style="width:${size}px;height:${size}px;line-height:${size}px">${n}</div>`,
        className: '',
        iconSize: [size, size],
      });
    },
  });

  geocoded.forEach(e => {
    const marker = L.marker([e.lat, e.lng], {
      icon: L.divIcon({
        className: '',
        html: `<div class="map-marker prio-${e.priority ?? 'medium'}"><span class="map-marker-dot"></span></div>`,
        iconSize: [34, 34],
        iconAnchor: [17, 34],
      }),
    });

    const isDoc = 'specialty' in e;
    const tag   = isDoc ? 'DOCTEUR' : 'PHARMACIE';
    const name  = e.full_name || e.name;
    const sub   = e.specialty || (isDoc ? 'Médecin' : 'Pharmacie');
    const addr  = e.address  ? `<div class="pic2-row"><span>📍</span> <span>${e.address}</span></div>` : '';
    const phone = e.phone    ? `<div class="pic2-row"><span>📞</span> <span style="color:#0284c7">${e.phone}</span></div>` : '';

    marker.bindPopup(`
      <div class="pic2-tooltip">
        <div class="pic2-tag">${tag}</div>
        <div class="pic2-name">${name}</div>
        <div class="pic2-sub">${sub}</div>
        <div class="pic2-details">${addr}${phone}</div>
        <button class="pic2-btn" onclick="toggleSelectById(${e.id})">Ajouter à ma journée</button>
      </div>`, { offset: [0, -28], className: 'pic2-leaflet-tooltip' });

    marker.on('click', () => showVisitPanel(e));
    cluster.addLayer(marker);
    State.markers.push(marker);
  });

  State._clusterGroup = cluster;
  State.map.addLayer(cluster);
}

window.toggleSelectById = function(id) {
  if (State.selectedIds.has(id)) {
    State.selectedIds.delete(id);
  } else {
    State.selectedIds.add(id);
  }
  renderEntityList();
  updateOptimizeButton();
};

function clearMapLayers() {
  if (State._clusterGroup) {
    State.map.removeLayer(State._clusterGroup);
    State._clusterGroup = null;
  }
  State.markers.forEach(m => { try { State.map.removeLayer(m); } catch(e) {} });
  State.markers = [];
  if (State.routeLayer) {
    State.map.removeLayer(State.routeLayer);
    State.routeLayer = null;
  }
}

function prioColor(p) {
  return { high: '#f43f5e', medium: '#f59e0b', low: '#22c55e' }[p] ?? '#4f8ef7';
}

// ─── User Location (Live GPS Tracking) ───────────────────────────────────────

/**
 * Start continuous GPS tracking via the browser Geolocation API.
 * Uses watchPosition to automatically update the user's position.
 * Falls back to cached location while waiting for GPS lock.
 */
function requestUserLocation() {
  if (!navigator.geolocation) {
    renderLocationStatus('unavailable');
    useCachedLocationFallback();
    return;
  }

  renderLocationStatus('requesting');

  // First try to restore cached location immediately (while GPS is locking)
  const cached = localStorage.getItem('pharmavisit_last_location');
  if (cached) {
    try {
      const loc = JSON.parse(cached);
      if (loc.lat && loc.lng) {
        State.userLocation = { lat: loc.lat, lng: loc.lng, name: 'Last Known Location', type: 'cached' };
        updateLocationMarker();
        // Don't change status yet — GPS is still trying
      }
    } catch (e) {}
  }

  // Start live GPS watch — this keeps tracking and updating
  State._gpsWatchId = navigator.geolocation.watchPosition(
    (pos) => {
      State.userLocation = {
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        name: 'Your Current Location',
        type: 'gps',
        accuracy: pos.coords.accuracy,
      };
      // Cache it
      localStorage.setItem('pharmavisit_last_location', JSON.stringify(State.userLocation));
      updateLocationMarker();
      renderLocationStatus('gps');
    },
    (err) => {
      console.warn('[PharmaVisit] GPS error:', err.message);
      // If we already have a cached location, use it
      if (State.userLocation) {
        renderLocationStatus(State.userLocation.type === 'gps' ? 'gps' : 'cached');
      } else {
        useCachedLocationFallback();
      }
    },
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 60000,
    }
  );

  // Also do a one-shot getCurrentPosition for faster first lock
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      State.userLocation = {
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        name: 'Your Current Location',
        type: 'gps',
        accuracy: pos.coords.accuracy,
      };
      localStorage.setItem('pharmavisit_last_location', JSON.stringify(State.userLocation));
      updateLocationMarker();
      renderLocationStatus('gps');
    },
    () => {}, // watchPosition handles errors
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
  );
}

/**
 * Use cached location when GPS is completely unavailable.
 */
function useCachedLocationFallback() {
  const cached = localStorage.getItem('pharmavisit_last_location');
  if (cached) {
    try {
      const loc = JSON.parse(cached);
      if (loc.lat && loc.lng) {
        State.userLocation = { lat: loc.lat, lng: loc.lng, name: 'Last Known Location', type: 'cached' };
        updateLocationMarker();
        renderLocationStatus('cached');
        return;
      }
    } catch (e) {}
  }
  renderLocationStatus('unavailable');
}

/**
 * Show / update the user's location marker on the map.
 */
function updateLocationMarker() {
  if (!State.userLocation) return;

  const { lat, lng, name, type, accuracy } = State.userLocation;

  // Remove old marker
  if (State.locationMarker) {
    State.map.removeLayer(State.locationMarker);
    State.locationMarker = null;
  }
  if (State._accuracyCircle) {
    State.map.removeLayer(State._accuracyCircle);
    State._accuracyCircle = null;
  }

  const isGps = type === 'gps';

  State.locationMarker = L.marker([lat, lng], {
    icon: L.divIcon({
      className: '',
      html: `<div class="my-location-marker ${isGps ? 'loc-marker-gps' : 'loc-marker-cached'}">
               <span class="loc-pulse"></span>
               <span class="loc-dot"></span>
             </div>`,
      iconSize: [40, 40],
      iconAnchor: [20, 20],
    }),
    zIndexOffset: 1000,
  }).addTo(State.map);

  State.locationMarker.bindTooltip(`<b>📍 Start:</b> ${name}`, {
    permanent: false,
    direction: 'top',
    offset: [0, -16],
  });

  // Show accuracy circle for GPS
  if (isGps && accuracy && accuracy < 5000) {
    State._accuracyCircle = L.circle([lat, lng], {
      radius: accuracy,
      color: '#3b82f6',
      fillColor: '#3b82f6',
      fillOpacity: 0.08,
      weight: 1,
      opacity: 0.3,
    }).addTo(State.map);
  }
}

/**
 * Render the location status indicator in the sidebar.
 */
function renderLocationStatus(status) {
  const el = document.getElementById('location-status');
  if (!el) return;

  const configs = {
    requesting: {
      icon: '⏳',
      text: 'Getting your location…',
      cls: 'loc-status-requesting',
      action: '',
    },
    gps: {
      icon: '📍',
      text: 'GPS location active',
      cls: 'loc-status-ok',
      action: '',
    },
    cached: {
      icon: '📌',
      text: 'Using last known location',
      cls: 'loc-status-cached',
      action: `<button class="loc-refresh-btn" onclick="requestUserLocation()" title="Retry GPS">↻</button>`,
    },
    unavailable: {
      icon: '⚠️',
      text: 'Enable location in browser',
      cls: 'loc-status-unavailable',
      action: `<button class="loc-refresh-btn" onclick="requestUserLocation()" title="Retry GPS">Retry</button>`,
    },
  };

  const cfg = configs[status] || configs.unavailable;
  el.className = `location-status ${cfg.cls}`;
  el.innerHTML = `
    <span class="loc-icon">${cfg.icon}</span>
    <span class="loc-text">${cfg.text}</span>
    <span class="loc-actions">${cfg.action}</span>
  `;
}

// ─── Optimization ─────────────────────────────────────────────────────────────

async function optimizeRoute() {
  if (State.selectedIds.size < 1) return;

  const btn = document.getElementById('btn-optimize');
  btn.classList.add('loading');

  try {
    const doctorIds = [...State.selectedIds];

    // If GPS hasn't locked yet, wait up to 8s for it
    if (!State.userLocation) {
      showLoading('Waiting for GPS lock…');
      await new Promise(resolve => {
        const deadline = Date.now() + 8000;
        const check = setInterval(() => {
          if (State.userLocation || Date.now() >= deadline) {
            clearInterval(check);
            resolve();
          }
        }, 200);
      });
    }

    // Still nothing? Can't proceed without a location
    if (!State.userLocation) {
      btn.classList.remove('loading');
      hideLoading();
      showToast('Location unavailable — please enable GPS in your browser settings', 'error');
      renderLocationStatus('unavailable');
      return;
    }

    const { lat: startLat, lng: startLng, name: startName } = State.userLocation;
    showLoading('Optimizing your route…');

    const result = await api('POST', '/routes/optimize', {
      doctor_ids: doctorIds,
      start_lat:  startLat,
      start_lng:  startLng,
      start_name: startName,
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

    const stopInfo = State.doctors.find(d => d.id === stop.id) || State.pharmacies.find(p => p.id === stop.id) || stop;
    const isDoc = 'specialty' in stopInfo;
    const tag = isDoc ? 'DOCTEUR' : 'PHARMACIE';
    const name = stopInfo.full_name || stopInfo.name;
    const sub = stopInfo.specialty ? stopInfo.specialty : (isDoc ? 'Médecin' : 'Pharmacie');
    const addr = stopInfo.address ? `<div class="pic2-row"><span>📍</span> <span>${stopInfo.address}</span></div>` : '';
    const phone = stopInfo.phone ? `<div class="pic2-row"><span>📞</span> <span style="color:#0284c7">${stopInfo.phone}</span></div>` : '';
    const coords = `<div class="pic2-row"><span>🌐</span> <span style="color:#6b7280">${stop.lat.toFixed(6)}, ${stop.lng.toFixed(6)}</span></div>`;
    
    const tooltipHtml = `
      <div class="pic2-tooltip">
        <div class="pic2-tag">${tag}</div>
        <div class="pic2-name">${name}</div>
        <div class="pic2-sub">${sub}</div>
        <div class="pic2-details">
          ${addr}
          ${phone}
          ${coords}
        </div>
      </div>
    `;
    m.bindPopup(tooltipHtml, { offset: [0, -28], className: 'pic2-leaflet-tooltip' });

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

  const addrRow = document.getElementById('visit-panel-address-row');
  const addrEl  = document.getElementById('visit-panel-address');
  if (entity.address) {
    addrRow.style.display = 'flex';
    addrEl.textContent = entity.address;
  } else {
    addrRow.style.display = 'none';
  }

  const phoneRow = document.getElementById('visit-panel-phone-row');
  const phoneEl  = document.getElementById('visit-panel-phone');
  if (entity.phone) {
    phoneRow.style.display = 'flex';
    phoneEl.textContent = entity.phone;
    phoneEl.href = `tel:${entity.phone}`;
  } else {
    phoneRow.style.display = 'none';
  }

  const coordsRow = document.getElementById('visit-panel-coords-row');
  const coordsEl  = document.getElementById('visit-panel-coords');
  if (entity.lat && entity.lng) {
    coordsRow.style.display = 'flex';
    coordsEl.textContent = `${Number(entity.lat).toFixed(6)}, ${Number(entity.lng).toFixed(6)}`;
  } else {
    coordsRow.style.display = 'none';
  }

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

  // Sidebar Toggle via Logo
  const floatingLogo = document.getElementById('floating-logo-btn');
  const sidebar = document.getElementById('sidebar');

  floatingLogo?.addEventListener('click', () => {
    sidebar.classList.remove('collapsed');
    floatingLogo.style.opacity = '0';
    floatingLogo.style.pointerEvents = 'none';
  });

  document.querySelector('#sidebar-header .logo')?.addEventListener('click', () => {
    sidebar.classList.add('collapsed');
    floatingLogo.style.opacity = '1';
    floatingLogo.style.pointerEvents = 'auto';
  });

  // Init logo state
  if (sidebar && !sidebar.classList.contains('collapsed') && floatingLogo) {
    floatingLogo.style.opacity = '0';
    floatingLogo.style.pointerEvents = 'none';
  }

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
