<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="PharmaVisit CRM — Field service routing for pharma sales reps">
  <title>PharmaVisit CRM</title>

  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

  <!-- Leaflet CSS (served locally) -->
  <link rel="stylesheet" href="/css/vendor/leaflet.css">
  <!-- Leaflet MarkerCluster CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css">
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css">

  <!-- App CSS -->
  <link rel="stylesheet" href="/css/pharmavisit.css?v=5">
</head>
<body>

<!-- ── Login overlay ─────────────────────────────────────────────────────── -->
<div id="login-overlay">
  <div class="login-bg-orbs"></div>
  <div class="login-card">
    <div class="login-logo">
      <img class="icon" src="/img/app_logo.png" alt="PharmaVisit Logo" style="object-fit: cover; border-radius: 14px;">
      <h2>PharmaVisit</h2>
      <p>Sign in to your rep dashboard</p>
    </div>

    <div class="login-field">
      <label for="login-email">Email address</label>
      <input type="email" id="login-email" placeholder="you@pharmavisit.ma" autocomplete="email">
    </div>
    <div class="login-field">
      <label for="login-password">Password</label>
      <input type="password" id="login-password" placeholder="••••••••" autocomplete="current-password">
    </div>

    <button id="btn-login">Sign in</button>
    <div id="login-error" class="login-error"></div>

    <p style="margin-top:16px; font-size:11px; color:var(--text-muted); text-align:center;">
      Demo: sarah@pharmavisit.ma / password
    </p>
  </div>
</div>

<!-- ── Main application ───────────────────────────────────────────────────── -->
<div id="app">

  <!-- Floating Logo (visible when sidebar is collapsed) -->
  <button id="floating-logo-btn" class="floating-logo-btn" title="Show Sidebar">
    <img src="/img/app_logo.png" alt="Logo">
  </button>

  <!-- Sidebar -->
  <aside id="sidebar">

    <!-- Header: logo + rep card -->
    <div id="sidebar-header">
      <div class="logo">
        <img class="logo-icon" src="/img/app_logo.png" alt="PharmaVisit Logo" style="object-fit: cover; border-radius: var(--radius-sm);">
        <div class="logo-text">
          <h1>PharmaVisit</h1>
          <p>Field Rep Dashboard</p>
        </div>
      </div>
      <div class="rep-card">
        <img class="rep-avatar" src="/img/rep_avatar.png" alt="Rep Avatar" style="object-fit: cover;">
        <div class="rep-info">
          <div class="rep-name" id="rep-name">Loading…</div>
          <div class="rep-territory" id="rep-territory">—</div>
        </div>
        <button class="btn-logout" id="btn-logout" title="Sign out"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg></button>
      </div>
    </div>

    <!-- Stats bar -->
    <div id="stats-bar">
      <div class="stat-item">
        <div class="stat-value" id="stat-doctors">—</div>
        <div class="stat-label">Doctors</div>
      </div>
      <div class="stat-item">
        <div class="stat-value" id="stat-pharmacies">—</div>
        <div class="stat-label">Pharmacies</div>
      </div>
      <div class="stat-item">
        <div class="stat-value" id="stat-reps">—</div>
        <div class="stat-label">Reps</div>
      </div>
    </div>

    <!-- Location status indicator -->
    <div id="location-status" class="location-status loc-status-requesting">
      <span class="loc-icon">⏳</span>
      <span class="loc-text">Getting your location…</span>
      <span class="loc-actions"></span>
    </div>

    <!-- Tabs -->
    <div id="tabs">
      <button class="tab-btn active" data-tab="doctors"><svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> Doctors</button>
      <button class="tab-btn" data-tab="pharmacies"><svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/></svg> Pharmacies</button>
    </div>

    <!-- Search -->
    <div id="search-bar">
      <div class="search-input-wrap">
        <span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg></span>
        <input type="search" id="search-input" placeholder="Search by name, specialty, city…">
      </div>
    </div>

    <!-- Entity list -->
    <div id="entity-list">
      <div class="empty-state"><div class="icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4"/><path d="m16.2 7.8 2.9-2.9"/><path d="M18 12h4"/><path d="m16.2 16.2 2.9 2.9"/><path d="M12 18v4"/><path d="m4.9 19.1 2.9-2.9"/><path d="M2 12h4"/><path d="m4.9 4.9 2.9 2.9"/></svg></div><p>Loading…</p></div>
    </div>

    <!-- Footer: optimize button -->
    <div id="sidebar-footer">
      <div class="selection-info" id="selection-info">Select doctors to plan your route</div>
      <button id="btn-optimize" disabled>
        <div class="spinner"></div>
        <span class="btn-text"><svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg> Optimize My Day</span>
      </button>
    </div>

  </aside>

  <!-- Map area -->
  <main id="map-area">
    <div id="map"></div>

    <!-- Loading overlay (shown during optimization) -->
    <div id="loading-overlay">
      <svg class="pulse-line" viewBox="0 0 200 40" fill="none"><polyline stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" points="0,20 25,20 35,20 45,6 55,34 65,12 75,28 85,20 115,20 125,20 135,6 145,34 155,12 165,28 175,20 200,20"/></svg>
      <div class="loading-text" id="loading-text">Optimizing your route…</div>
    </div>

    <!-- Route summary card (top-right) -->
    <div id="route-summary"></div>

    <!-- Visit log panel (slides up from bottom) -->
    <div id="visit-panel">
      <input type="hidden" id="visit-doctor-id">
      <input type="hidden" id="visit-pharmacy-id">

      <h3 id="visit-panel-name">Doctor Name</h3>
      <p class="sub" id="visit-panel-sub">Specialty · City</p>

      <div class="visit-panel-contact">
        <div class="contact-item" id="visit-panel-address-row">
          <svg class="ico text-prio-high" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
          <span id="visit-panel-address"></span>
        </div>
        <div class="contact-item" id="visit-panel-phone-row">
          <svg class="ico text-prio-high" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
          <a href="#" id="visit-panel-phone" class="text-accent" style="text-decoration:none;"></a>
        </div>
        <div class="contact-item" id="visit-panel-coords-row">
          <svg class="ico text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><path d="M2 12h20"/></svg>
          <span id="visit-panel-coords"></span>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group" style="flex:2">
          <label for="visit-notes">Visit notes</label>
          <textarea id="visit-notes" class="form-control" rows="2"
                    placeholder="How did the visit go?"></textarea>
        </div>
        <div class="form-group">
          <label for="visit-duration">Duration (min)</label>
          <input type="number" id="visit-duration" class="form-control" placeholder="30" min="1" max="480">
        </div>
        <div class="form-group">
          <label for="visit-outcome">Outcome</label>
          <select id="visit-outcome" class="form-control">
            <option value="completed">Completed</option>
            <option value="no_show">No show</option>
            <option value="rescheduled">Rescheduled</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      <div class="panel-actions">
        <button class="btn-secondary" id="btn-close-panel">Cancel</button>
        <button class="btn-primary" id="btn-submit-visit">Log Visit</button>
      </div>
    </div>
  </main>

</div>

<!-- Toast container -->
<div id="toast-container"></div>

<!-- Leaflet JS (served locally) -->
<script src="/js/vendor/leaflet.js"></script>
<script>if (typeof L === 'undefined' && window.leaflet) { window.L = window.leaflet; }</script>
<!-- Leaflet MarkerCluster JS -->
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

<!-- App JS -->
<script src="/js/pharmavisit.js?v=5"></script>

</body>
</html>
