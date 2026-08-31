(function () {
  const SITES = [
    {
      name: "DrSumaiya.com",
      slug: "dr-sumaiya-com",
      url: "https://drsumaiya.com/"
    },
    {
      name: "IQS",
      slug: "iqs",
      url: "https://iqs.org.in/"
    }
  ];

  let currentSiteIndex = 0;
  let currentStrategy = "mobile"; // 'mobile' | 'desktop'
  const siteData = {};

  function getScoreClass(score) {
    if (score >= 90) return "score-good";
    if (score >= 50) return "score-average";
    return "score-poor";
  }

  function getCircleOffset(score) {
    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const validScore = Math.max(0, Math.min(100, score || 0));
    return circumference - (validScore / 100) * circumference;
  }

  async function fetchSiteData(site) {
    const rawUrl = `https://raw.githubusercontent.com/drsumaiya/drsumaiya.com-upptime/master/pagespeed/${site.slug}/latest.json`;
    try {
      const res = await fetch(rawUrl, { cache: "no-store" });
      if (!res.ok) throw new Error("Fetch failed");
      const data = await res.json();
      siteData[site.slug] = data;
    } catch (e) {
      console.warn(`Could not fetch live PageSpeed data for ${site.name}:`, e);
      // Fallback template
      siteData[site.slug] = {
        name: site.name,
        url: site.url,
        timestamp: new Date().toISOString(),
        mobile: {
          performance: 0,
          accessibility: 0,
          bestPractices: 0,
          seo: 0,
          coreWebVitals: {
            firstContentfulPaint: "Pending audit",
            largestContentfulPaint: "Pending audit",
            totalBlockingTime: "Pending audit",
            cumulativeLayoutShift: "Pending audit",
            speedIndex: "Pending audit"
          }
        },
        desktop: {
          performance: 0,
          accessibility: 0,
          bestPractices: 0,
          seo: 0,
          coreWebVitals: {
            firstContentfulPaint: "Pending audit",
            largestContentfulPaint: "Pending audit",
            totalBlockingTime: "Pending audit",
            cumulativeLayoutShift: "Pending audit",
            speedIndex: "Pending audit"
          }
        }
      };
    }
  }

  function renderGauge(label, score) {
    const radius = 40;
    const circumference = (2 * Math.PI * radius).toFixed(1);
    const offset = getCircleOffset(score).toFixed(1);
    const scoreClass = getScoreClass(score);

    return `
      <div class="psi-gauge-card">
        <div class="psi-gauge-svg-wrapper">
          <svg class="psi-gauge-svg" viewBox="0 0 100 100">
            <circle class="psi-gauge-bg" cx="50" cy="50" r="${radius}"></circle>
            <circle class="psi-gauge-meter ${scoreClass}" cx="50" cy="50" r="${radius}"
              stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"></circle>
          </svg>
          <span class="psi-gauge-score ${scoreClass}">${score || 0}</span>
        </div>
        <div class="psi-gauge-label">${label}</div>
      </div>
    `;
  }

  function renderDashboard() {
    const container = document.getElementById("pagespeed-container");
    if (!container) return;

    const currentSite = SITES[currentSiteIndex];
    const data = siteData[currentSite.slug] || {};
    const strategyData = data[currentStrategy] || {
      performance: 0,
      accessibility: 0,
      bestPractices: 0,
      seo: 0,
      coreWebVitals: {}
    };

    const vitals = strategyData.coreWebVitals || {};
    const dateFormatted = data.timestamp ? new Date(data.timestamp).toLocaleString() : "Recently";
    const livePsiUrl = `https://pagespeed.web.dev/analysis?url=${encodeURIComponent(currentSite.url)}`;

    container.innerHTML = `
      <section id="pagespeed-section" class="psi-dashboard-wrapper">
        <div class="psi-header">
          <h2 class="psi-title">
            <span>⚡</span> PageSpeed Insights & Web Vitals
          </h2>
          <p class="psi-subtitle">
            Automated Google Lighthouse and Core Web Vitals performance benchmarks
          </p>
        </div>

        <div class="psi-controls">
          <div class="psi-tabs" role="tablist">
            ${SITES.map((site, idx) => `
              <button class="psi-tab-btn ${idx === currentSiteIndex ? 'active' : ''}" data-site-idx="${idx}">
                ${site.name}
              </button>
            `).join('')}
          </div>

          <div class="psi-strategy-toggle">
            <button class="psi-tab-btn ${currentStrategy === 'mobile' ? 'active' : ''}" data-strategy="mobile">
              📱 Mobile
            </button>
            <button class="psi-tab-btn ${currentStrategy === 'desktop' ? 'active' : ''}" data-strategy="desktop">
              🖥️ Desktop
            </button>
          </div>
        </div>

        <div class="psi-meta-bar">
          <span>🕒 Last Audited: <strong>${dateFormatted}</strong></span>
          <a href="${livePsiUrl}" target="_blank" rel="noopener noreferrer" class="psi-live-link">
            Run Live on PageSpeed.web.dev ↗
          </a>
        </div>

        <div class="psi-scores-grid">
          ${renderGauge("Performance", strategyData.performance)}
          ${renderGauge("Accessibility", strategyData.accessibility)}
          ${renderGauge("Best Practices", strategyData.bestPractices)}
          ${renderGauge("SEO", strategyData.seo)}
        </div>

        <div class="psi-vitals-section">
          <div class="psi-vitals-header">
            <h3 class="psi-vitals-title">Core Web Vitals & Metrics</h3>
            <div class="psi-legend">
              <div class="psi-legend-item"><span class="psi-legend-dot dot-good"></span> 90-100 (Good)</div>
              <div class="psi-legend-item"><span class="psi-legend-dot dot-average"></span> 50-89 (Average)</div>
              <div class="psi-legend-item"><span class="psi-legend-dot dot-poor"></span> 0-49 (Poor)</div>
            </div>
          </div>

          <div class="psi-vitals-grid">
            <div class="psi-vital-card">
              <div class="psi-vital-metric">First Contentful Paint</div>
              <div class="psi-vital-value">${vitals.firstContentfulPaint || 'N/A'}</div>
              <div class="psi-vital-desc">Time until the first text or image is painted</div>
            </div>
            <div class="psi-vital-card">
              <div class="psi-vital-metric">Largest Contentful Paint</div>
              <div class="psi-vital-value">${vitals.largestContentfulPaint || 'N/A'}</div>
              <div class="psi-vital-desc">Time when the main content has likely loaded</div>
            </div>
            <div class="psi-vital-card">
              <div class="psi-vital-metric">Total Blocking Time</div>
              <div class="psi-vital-value">${vitals.totalBlockingTime || 'N/A'}</div>
              <div class="psi-vital-desc">Sum of periods blocking user input</div>
            </div>
            <div class="psi-vital-card">
              <div class="psi-vital-metric">Cumulative Layout Shift</div>
              <div class="psi-vital-value">${vitals.cumulativeLayoutShift || 'N/A'}</div>
              <div class="psi-vital-desc">Visual stability of page elements</div>
            </div>
            <div class="psi-vital-card">
              <div class="psi-vital-metric">Speed Index</div>
              <div class="psi-vital-value">${vitals.speedIndex || 'N/A'}</div>
              <div class="psi-vital-desc">How quickly contents are visually populated</div>
            </div>
          </div>
        </div>
      </section>
    `;

    // Attach event listeners
    container.querySelectorAll('[data-site-idx]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentSiteIndex = parseInt(btn.getAttribute('data-site-idx'), 10);
        renderDashboard();
      });
    });

    container.querySelectorAll('[data-strategy]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentStrategy = btn.getAttribute('data-strategy');
        renderDashboard();
      });
    });
  }

  async function init() {
    // Check if target container exists, otherwise wait or inject
    let container = document.getElementById("pagespeed-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "pagespeed-container";
      const main = document.querySelector("main") || document.body;
      main.appendChild(container);
    }

    // Load data for all sites
    await Promise.all(SITES.map(fetchSiteData));
    renderDashboard();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
