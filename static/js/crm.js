/* =========================================
   Poytakht CRM — Main JS
   ========================================= */

document.addEventListener('DOMContentLoaded', function () {

  // ---- SIDEBAR TOGGLE (mobile) ----
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const main = document.getElementById('main');

  if (toggleBtn && sidebar) {
    // Create overlay
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
      if (sidebar.classList.contains('open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    overlay.addEventListener('click', closeSidebar);

    // Close sidebar when nav item clicked on mobile
    sidebar.querySelectorAll('.nav-item').forEach(function (item) {
      item.addEventListener('click', function () {
        if (window.innerWidth <= 767) closeSidebar();
      });
    });
  }

  // ---- AUTO-DISMISS ALERTS ----
  document.querySelectorAll('.crm-alert').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // ---- ACTIVE NAV HIGHLIGHT (mobile bottom nav) ----
  const currentPath = window.location.pathname;
  document.querySelectorAll('.mob-nav-item').forEach(function (item) {
    if (item.getAttribute('href') && currentPath.startsWith(item.getAttribute('href')) && item.getAttribute('href') !== '/') {
      item.classList.add('active');
    }
  });

  // ---- NUMBER FORMAT INPUT ----
  document.querySelectorAll('input[type="number"]').forEach(function (input) {
    input.addEventListener('input', function () {
      // Optional: format display
    });
  });

  // ---- CONFIRM DELETES ----
  document.querySelectorAll('[data-confirm]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm || 'Вы уверены?')) {
        e.preventDefault();
      }
    });
  });

  // ---- TOOLTIPS ----
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  // ---- PRICE CALCULATOR (apartment form) ----
  const areaInput = document.getElementById('id_area');
  const ppmInput = document.getElementById('id_price_per_sqm');
  const totalInput = document.getElementById('id_total_price');

  if (areaInput && ppmInput && totalInput) {
    function updateTotal() {
      const area = parseFloat(areaInput.value) || 0;
      const ppm = parseFloat(ppmInput.value) || 0;
      if (area > 0 && ppm > 0) {
        totalInput.value = (area * ppm).toFixed(2);
      }
    }
    areaInput.addEventListener('input', updateTotal);
    ppmInput.addEventListener('input', updateTotal);
  }

});
