<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="PharmaVisit CRM — Field service routing for pharma sales reps">
  <title>PharmaVisit CRM</title>

  <!-- Leaflet CSS (served locally — no SRI check needed) -->
  <link rel="stylesheet" href="/css/vendor/leaflet.css">

  <!-- App CSS -->
  <link rel="stylesheet" href="/css/pharmavisit.css">
</head>
<body>

<!-- ── Login overlay ─────────────────────────────────────────────────────── -->
<div id="login-overlay">
  <div class="login-card">
    <div class="login-logo">
      <div class="icon">💊</div>
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

  <!-- Sidebar -->
  <aside id="sidebar">

    <!-- Header: logo + rep card -->
    <div id="sidebar-header">
      <div class="logo">
        <div class="logo-icon">💊</div>
        <div class="logo-text">
          <h1>PharmaVisit</h1>
          <p>Field Rep Dashboard</p>
        </div>
      </div>
      <div class="rep-card">
        <div class="rep-avatar" id="rep-initials">?</div>
        <div class="rep-info">
          <div class="rep-name" id="rep-name">Loading…</div>
          <div class="rep-territory" id="rep-territory">—</div>
        </div>
        <button class="btn-logout" id="btn-logout" title="Sign out">⏏</button>
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

    <!-- Tabs -->
    <div id="tabs">
      <button class="tab-btn active" data-tab="doctors">🩺 Doctors</button>
      <button class="tab-btn" data-tab="pharmacies">🏥 Pharmacies</button>
    </div>

    <!-- Search -->
    <div id="search-bar">
      <div class="search-input-wrap">
        <span>🔍</span>
        <input type="search" id="search-input" placeholder="Search by name, specialty, city…">
      </div>
    </div>

    <!-- Entity list -->
    <div id="entity-list">
      <div class="empty-state"><div class="icon">⏳</div><p>Loading…</p></div>
    </div>

    <!-- Footer: optimize button -->
    <div id="sidebar-footer">
      <div class="selection-info" id="selection-info">Select doctors to plan your route</div>
      <button id="btn-optimize" disabled>
        <div class="spinner"></div>
        <span class="btn-text">⚡ Optimize My Day</span>
      </button>
    </div>

  </aside>

  <!-- Map area -->
  <main id="map-area">
    <div id="map"></div>

    <!-- Loading overlay (shown during optimization) -->
    <div id="loading-overlay">
      <div class="loading-spinner"></div>
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
            <option value="completed">✅ Completed</option>
            <option value="no_show">❌ No show</option>
            <option value="rescheduled">📅 Rescheduled</option>
            <option value="cancelled">🚫 Cancelled</option>
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

<!-- Leaflet JS (served locally — no SRI/CDN issues) -->
<script src="/js/vendor/leaflet.js"></script>
<!-- Bridge: normalize export name (some Leaflet builds export window.leaflet instead of window.L) -->
<script>if (typeof L === 'undefined' && window.leaflet) { window.L = window.leaflet; }</script>

<!-- App JS -->
<script src="/js/pharmavisit.js"></script>

</body>
</html>
