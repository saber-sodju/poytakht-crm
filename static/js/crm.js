/* =========================================
   Poytakht CRM — Main JS
   Gold & Cream Theme — Enhanced UI
   ========================================= */

document.addEventListener('DOMContentLoaded', function () {

  /* ── SIDEBAR TOGGLE (mobile) ─────────────────────────── */
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebar   = document.getElementById('sidebar');

  if (toggleBtn && sidebar) {
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);

    function openSidebar() {
      sidebar.classList.add('open');
      overlay.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
    function closeSidebar() {
      sidebar.classList.remove('open');
      overlay.classList.remove('active');
      document.body.style.overflow = '';
    }

    toggleBtn.addEventListener('click', function () {
      sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });
    overlay.addEventListener('click', closeSidebar);

    sidebar.querySelectorAll('.nav-item').forEach(function (item) {
      item.addEventListener('click', function () {
        if (window.innerWidth <= 767) closeSidebar();
      });
    });
  }

  /* ── AUTO-DISMISS ALERTS ─────────────────────────────── */
  document.querySelectorAll('.crm-alert').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  /* ── ACTIVE NAV HIGHLIGHT (mobile bottom nav) ────────── */
  const currentPath = window.location.pathname;
  document.querySelectorAll('.mob-nav-item').forEach(function (item) {
    const href = item.getAttribute('href');
    if (href && href !== '/' && currentPath.startsWith(href)) {
      item.classList.add('active');
    }
  });

  /* ── CONFIRM DELETES ─────────────────────────────────── */
  document.querySelectorAll('[data-confirm]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm || 'Вы уверены?')) e.preventDefault();
    });
  });

  /* ── TOOLTIPS ────────────────────────────────────────── */
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  /* ── PRICE CALCULATOR (apartment form) ──────────────── */
  const areaInput  = document.getElementById('id_area');
  const ppmInput   = document.getElementById('id_price_per_sqm');
  const totalInput = document.getElementById('id_total_price');
  if (areaInput && ppmInput && totalInput) {
    function updateTotal() {
      const area = parseFloat(areaInput.value) || 0;
      const ppm  = parseFloat(ppmInput.value)  || 0;
      if (area > 0 && ppm > 0) totalInput.value = (area * ppm).toFixed(2);
    }
    areaInput.addEventListener('input', updateTotal);
    ppmInput.addEventListener('input', updateTotal);
  }

  /* ═══════════════════════════════════════════════════════
     ANIMATIONS & MODERN INTERACTIONS
     ═══════════════════════════════════════════════════════ */

  /* ── 1. SCROLL PROGRESS BAR ──────────────────────────── */
  const progressBar = document.createElement('div');
  progressBar.className = 'scroll-progress';
  document.body.appendChild(progressBar);

  function updateProgress() {
    const scrollTop  = window.scrollY;
    const docHeight  = document.documentElement.scrollHeight - window.innerHeight;
    const pct        = docHeight > 0 ? Math.min((scrollTop / docHeight) * 100, 100) : 0;
    progressBar.style.width = pct + '%';
  }
  window.addEventListener('scroll', updateProgress, { passive: true });
  updateProgress();

  /* ── 2. TOPBAR SHADOW ON SCROLL ──────────────────────── */
  const topbar = document.getElementById('topbar');
  if (topbar) {
    window.addEventListener('scroll', function () {
      topbar.classList.toggle('scrolled', window.scrollY > 8);
    }, { passive: true });
  }

  /* ── 3. BUTTON RIPPLE EFFECT ─────────────────────────── */
  function addRipple(e) {
    const btn  = e.currentTarget;
    const rect = btn.getBoundingClientRect();
    const rip  = document.createElement('span');
    rip.className   = 'btn-ripple';
    rip.style.left  = (e.clientX - rect.left  - 4) + 'px';
    rip.style.top   = (e.clientY - rect.top - 4) + 'px';
    btn.appendChild(rip);
    setTimeout(function () { rip.remove(); }, 600);
  }
  document.querySelectorAll('.btn-gold, .btn-outline-gold').forEach(function (btn) {
    btn.addEventListener('click', addRipple);
  });

  /* ── 4. ANIMATED NUMBER COUNTERS (KPI values) ─────────── */
  function animateCounter(el, duration) {
    duration = duration || 950;
    var text = el.textContent.trim();

    /* Extract first integer from text: handles "$105 000", "120", "3 чел." etc. */
    var match = text.match(/\d[\d\s]*/);
    if (!match) return;

    var raw    = match[0].replace(/\s/g, '');
    var target = parseInt(raw, 10);
    if (!target || isNaN(target) || target > 9999999) return;

    var prefix = text.slice(0, text.indexOf(match[0]));
    var suffix = text.slice(text.indexOf(match[0]) + match[0].length);
    var start  = null;

    function easeOutExpo(t) {
      return t === 1 ? 1 : 1 - Math.pow(2, -9 * t);
    }

    function tick(timestamp) {
      if (!start) start = timestamp;
      var progress = Math.min((timestamp - start) / duration, 1);
      var eased    = easeOutExpo(progress);
      var current  = Math.round(eased * target);

      /* Format with space thousands separator (ru style) */
      var formatted = current.toLocaleString('ru-RU');
      el.textContent = prefix + formatted + suffix;

      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = text; /* restore exact original */
      }
    }
    requestAnimationFrame(tick);
  }

  /* Run counters on all .kpi-value elements */
  document.querySelectorAll('.kpi-value').forEach(function (el) {
    animateCounter(el);
  });

  /* ── 5. PROGRESS BARS: animate from 0 to value ────────── */
  document.querySelectorAll('.progress-bar').forEach(function (bar) {
    var target = bar.style.width || bar.getAttribute('aria-valuenow') + '%';
    bar.style.width = '0%';
    setTimeout(function () { bar.style.width = target; }, 100);
  });

  /* ── 6. INTERSECTION OBSERVER — scroll-trigger cards ──── */
  var ioOptions = { threshold: 0.1, rootMargin: '0px 0px -40px 0px' };
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.style.animationPlayState = 'running';
        io.unobserve(entry.target);
      }
    });
  }, ioOptions);

  /* Pause animations and let IntersectionObserver start them */
  document.querySelectorAll('.crm-card, .form-card, .block-card, .stage-card').forEach(function (el) {
    /* Only delay if element is below the fold */
    if (el.getBoundingClientRect().top > window.innerHeight) {
      el.style.animationPlayState = 'paused';
      io.observe(el);
    }
  });

  /* ── 7. SIDEBAR BRAND: goldGlow on logo ─────────────── */
  var logoImg = document.querySelector('.brand-logo-img');
  if (logoImg) {
    /* Subtle golden glow — fires once after 2s then stops */
    setTimeout(function () {
      logoImg.style.transition = 'box-shadow 0.4s ease';
      logoImg.style.boxShadow  = '0 0 0 2px rgba(212,175,55,0.5)';
      setTimeout(function () {
        logoImg.style.boxShadow = '';
      }, 1200);
    }, 1800);
  }

  /* ── 8. KEYBOARD SHORTCUT: / to focus search ─────────── */
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      e.preventDefault();
      var searchInput = document.querySelector('.search-input');
      if (searchInput) searchInput.focus();
    }
  });

  /* ── 9. TABLE ROW CLICK → follow first link (if any) ─── */
  document.querySelectorAll('.crm-table tbody tr[data-href]').forEach(function (row) {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function (e) {
      if (!e.target.closest('a, button, input, select')) {
        window.location.href = row.dataset.href;
      }
    });
  });

  /* ── 10. SMOOTH PAGE EXIT TRANSITION ─────────────────── */
  document.querySelectorAll('a[href]').forEach(function (link) {
    var href = link.getAttribute('href');
    /* Only internal same-origin links */
    if (!href || href.startsWith('#') || href.startsWith('mailto') ||
        href.startsWith('http') || link.hasAttribute('target')) return;
    /* Skip links inside forms or modals */
    if (link.closest('form, [data-bs-toggle]')) return;

    link.addEventListener('click', function (e) {
      /* Only if not modifier key (open in new tab etc.) */
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      var dest = href;
      var main = document.getElementById('main');
      if (main) {
        main.style.transition  = 'opacity 0.18s ease, transform 0.18s ease';
        main.style.opacity     = '0';
        main.style.transform   = 'translateY(6px)';
      }
      setTimeout(function () { window.location.href = dest; }, 180);
    });
  });

});
