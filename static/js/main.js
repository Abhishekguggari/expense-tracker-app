// ── Theme Toggle ─────────────────────────────────────────
(function () {
  const html = document.documentElement;
  
  // Retrieve saved theme from localStorage, or fallback to OS preference
  let currentTheme = localStorage.getItem('theme');
  if (!currentTheme) {
    currentTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  html.setAttribute('data-theme', currentTheme);

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.querySelector('[data-theme-toggle]');
    if (!btn) return;

    updateToggleIcon(btn, currentTheme);

    btn.addEventListener('click', () => {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', currentTheme);
      localStorage.setItem('theme', currentTheme); // Persist theme across page loads
      updateToggleIcon(btn, currentTheme);
      if (typeof initChart === 'function') initChart(); // Update chart colors
    });
  });

  function updateToggleIcon(btn, theme) {
    const span = btn.querySelector('span');
    
    const icon = btn.querySelector('i[data-lucide], svg.lucide');
    if (icon) {
      const svgSun = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-sun"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`;
      const svgMoon = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-moon"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`;
      
      const temp = document.createElement('div');
      temp.innerHTML = theme === 'dark' ? svgSun : svgMoon;
      icon.replaceWith(temp.firstChild);
    }

    if (span) span.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
    btn.setAttribute('aria-label', 'Switch to ' + (theme === 'dark' ? 'light' : 'dark') + ' mode');
  }
})();

// ── Sidebar Hamburger (Mobile) ────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const hamburger = document.getElementById('hamburger');
  const sidebar = document.getElementById('sidebar');

  if (!hamburger || !sidebar) return;

  // Create overlay
  const overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  document.body.appendChild(overlay);

  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  hamburger.addEventListener('click', () => {
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  });

  overlay.addEventListener('click', closeSidebar);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSidebar(); });
});

// ── Auto-fill Today's Date on Add Form ────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const dateInput = document.getElementById('date');
  if (dateInput && !dateInput.value) {
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
  }
});

// ── Flash auto-dismiss after 4s ──────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach(flash => {
    setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transform = 'translateY(-4px)';
      flash.style.transition = 'opacity 0.3s, transform 0.3s';
      setTimeout(() => flash.remove(), 300);
    }, 4000);
  });
});

// ── Animate category bars on load ────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const fills = document.querySelectorAll('.category-bar-fill');
  fills.forEach(fill => {
    const targetWidth = fill.style.width;
    fill.style.width = '0%';
    requestAnimationFrame(() => {
      fill.style.width = targetWidth;
    });
  });
});

// ── Chart.js Initialization ──────────────────────────────
let expenseChartInstance = null;
let lastMonthChartInstance = null;

function initChart() {
  const canvas = document.getElementById('expenseChart');
  if (!canvas) return;

  if (typeof ChartDataLabels !== 'undefined') {
    Chart.register(ChartDataLabels);
  }

  // Get CSS variables for theming
  const style = getComputedStyle(document.documentElement);
  const primaryColor = style.getPropertyValue('--color-primary').trim() || '#d4af37';
  const errorColor = style.getPropertyValue('--color-error').trim() || '#d163a7';
  const successColor = style.getPropertyValue('--color-success').trim() || '#6daa45';
  const warningColor = style.getPropertyValue('--color-warning').trim() || '#bb653b';
  const textColor = style.getPropertyValue('--color-text').trim() || '#fafafa';
  const bgColors = [
    primaryColor, errorColor, successColor, warningColor, 
    '#8b5cf6', '#3b82f6', '#14b8a6', '#f59e0b', '#f43f5e'
  ];

  // Custom tooltip to show percentages
  const tooltipOptions = {
    callbacks: {
      label: function(context) {
        const label = context.label || '';
        const value = context.raw;
        let total = 0;
        context.chart.data.datasets[0].data.forEach(d => total += d);
        const percentage = total > 0 ? ((value / total) * 100).toFixed(1) + '%' : '0%';
        return `${label}: ₹${value.toFixed(2)} (${percentage})`;
      }
    }
  };

  const dataLabelsOptions = {
    color: '#ffffff',
    font: { weight: '600', size: 12, family: 'Inter' },
    textStrokeColor: 'rgba(0, 0, 0, 0.5)',
    textStrokeWidth: 2,
    formatter: (value, context) => {
      let total = 0;
      context.chart.data.datasets[0].data.forEach(d => total += d);
      let percentage = (value * 100 / total).toFixed(1);
      return percentage >= 5 ? percentage + '%' : null;
    }
  };

  let thisMonthData = [];
  let lastMonthData = [];
  let thisMonthFetched = false;
  let lastMonthFetched = false;

  function renderComparison() {
    if (!thisMonthFetched || !lastMonthFetched) return;
    const container = document.getElementById('comparisonContainer');
    if (!container) return;

    let html = '<h4 style="font-size: var(--text-sm); font-weight: 600; color: var(--color-text); margin-bottom: var(--space-3); border-bottom: 1px solid var(--color-divider); padding-bottom: var(--space-2);">Comparison (This Month vs Last Month)</h4><div style="display:flex; flex-direction:column; gap:var(--space-2);">';
    
    const categories = new Set([...thisMonthData.map(d => d.category), ...lastMonthData.map(d => d.category)]);
    
    let hasDiff = false;
    categories.forEach(cat => {
      const current = thisMonthData.find(d => d.category === cat)?.total || 0;
      const last = lastMonthData.find(d => d.category === cat)?.total || 0;
      const diff = current - last;
      
      if (Math.abs(diff) > 0.01) {
        hasDiff = true;
        const color = diff > 0 ? 'var(--color-error)' : 'var(--color-success)';
        const text = diff > 0 ? `+₹${diff.toFixed(2)} (Extra)` : `-₹${Math.abs(diff).toFixed(2)} (Saved)`;
        html += `<div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="color: var(--color-text-muted);">${cat}</span>
          <span style="color:${color}; font-weight:600; font-variant-numeric: tabular-nums;">${text}</span>
        </div>`;
      }
    });

    if (!hasDiff) {
      html += '<div style="color:var(--color-text-muted); text-align:center;">No differences found.</div>';
    }
    html += '</div>';
    container.innerHTML = html;
  }

  // Fetch "This Month" data strictly for the comparison
  fetch('/api/current-month-category-data')
    .then(res => res.json())
    .then(data => {
      thisMonthFetched = true;
      thisMonthData = data || [];
      renderComparison();
    })
    .catch(err => {
      console.error("Current month data error:", err);
      thisMonthFetched = true;
      renderComparison();
    });

  fetch('/api/category-data' + window.location.search)
    .then(res => res.json())
    .then(data => {
      if (!data || data.length === 0) return;
      
      const labels = data.map(d => d.category);
      const values = data.map(d => d.total);
      
      if (expenseChartInstance) {
        expenseChartInstance.destroy();
      }

      expenseChartInstance = new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: bgColors,
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: {
            animateScale: true,
            animateRotate: true,
            duration: 1200,
            easing: 'easeOutQuart'
          },
          plugins: {
            legend: {
              position: 'right',
              labels: { color: textColor, font: { family: 'Inter' } }
            },
            tooltip: tooltipOptions,
            datalabels: dataLabelsOptions
          }
        }
      });
    })
    .catch(err => {
      console.error("Chart loading error:", err);
    });

  // Load Last Month Pie Chart
  const lmCanvas = document.getElementById('lastMonthChart');
  if (!lmCanvas) return;

  fetch('/api/last-month-category-data')
    .then(res => res.json())
    .then(data => {
      lastMonthFetched = true;
      lastMonthData = data || [];
      renderComparison();

      if (!data || data.length === 0) {
        const container = document.getElementById('lastMonthContainer');
        if (container && !container.dataset.emptyHandled) {
          container.innerHTML = '<p style="text-align:center; color:var(--color-text-muted); font-size:var(--text-sm); margin-top:2rem;">No expenses last month.</p>';
          container.dataset.emptyHandled = "true";
        }
        return;
      }
      
      const labels = data.map(d => d.category);
      const values = data.map(d => d.total);

      if (lastMonthChartInstance) {
        lastMonthChartInstance.destroy();
      }

      lastMonthChartInstance = new Chart(lmCanvas, {
        type: 'pie',
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: bgColors,
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: {
            animateScale: true,
            animateRotate: true,
            duration: 1200,
            easing: 'easeOutQuart'
          },
          plugins: {
            legend: {
              position: 'right',
              labels: { color: textColor, font: { family: 'Inter' } }
            },
            tooltip: tooltipOptions,
            datalabels: dataLabelsOptions
          }
        }
      });
    })
    .catch(err => {
      console.error("Last month chart error:", err);
      lastMonthFetched = true;
      renderComparison();
    });
}

document.addEventListener('DOMContentLoaded', initChart);
