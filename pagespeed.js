/**
 * PageSpeed Insights & Core Web Vitals Dashboard for Upptime
 * Version 1.1.0 - Dynamically mounted before footer
 */
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
    },
    {
      name: "IQS - Hifz Focus",
      slug: "iqs-hifz",
      url: "https://hifz.iqs.org.in/"
    }
  ];

  let currentSiteIndex = 0;
  let currentStrategy = "mobile"; // 'mobile' | 'desktop'
  let currentMetric = "performance"; // 'performance' | 'fcp' | 'lcp' | 'cls'
  const siteData = {};
  const siteHistory = {};

  const METRIC_CONFIG = {
    performance: {
      name: "Performance Score",
      unit: "/ 100",
      yMax: 100,
      yMin: 0,
      formatVal: v => Math.round(v),
      getScoreClass: v => (v >= 90 ? "score-good" : v >= 50 ? "score-average" : "score-poor")
    },
    fcp: {
      name: "First Contentful Paint (FCP)",
      unit: "s",
      formatVal: v => (v !== null ? v.toFixed(1) + " s" : "N/A"),
      getScoreClass: v => (v <= 1.8 ? "score-good" : v <= 3.0 ? "score-average" : "score-poor")
    },
    lcp: {
      name: "Largest Contentful Paint (LCP)",
      unit: "s",
      formatVal: v => (v !== null ? v.toFixed(1) + " s" : "N/A"),
      getScoreClass: v => (v <= 2.5 ? "score-good" : v <= 4.0 ? "score-average" : "score-poor")
    },
    cls: {
      name: "Cumulative Layout Shift (CLS)",
      unit: "",
      formatVal: v => (v !== null ? v.toFixed(3) : "N/A"),
      getScoreClass: v => (v <= 0.1 ? "score-good" : v <= 0.25 ? "score-average" : "score-poor")
    }
  };

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

  function parseMetricNumber(strategyObj, metricKey) {
    if (!strategyObj) return null;
    if (metricKey === "performance") {
      const p = strategyObj.performance;
      return typeof p === "number" && p > 0 ? p : null;
    }
    const vitals = strategyObj.coreWebVitals || {};
    if (metricKey === "fcp") {
      const val = vitals.firstContentfulPaint;
      if (!val || val === "N/A") return null;
      if (typeof val === "string" && val.includes("ms")) {
        return parseFloat(val.replace(/,/g, "")) / 1000;
      }
      return parseFloat(val) || null;
    }
    if (metricKey === "lcp") {
      const val = vitals.largestContentfulPaint;
      if (!val || val === "N/A") return null;
      if (typeof val === "string" && val.includes("ms")) {
        return parseFloat(val.replace(/,/g, "")) / 1000;
      }
      return parseFloat(val) || null;
    }
    if (metricKey === "cls") {
      const val = vitals.cumulativeLayoutShift;
      if (!val || val === "N/A") return null;
      const parsed = parseFloat(val);
      return !isNaN(parsed) ? parsed : null;
    }
    return null;
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

  async function fetchSiteHistory(site) {
    const rawUrl = `https://raw.githubusercontent.com/drsumaiya/drsumaiya.com-upptime/master/pagespeed/history/${site.slug}.jsonl`;
    try {
      const res = await fetch(rawUrl, { cache: "no-store" });
      if (!res.ok) throw new Error("Fetch history failed");
      const text = await res.text();
      const lines = text.trim().split("\n").filter(Boolean);
      const records = [];
      for (const line of lines) {
        try {
          const item = JSON.parse(line);
          const mPerf = item.mobile?.performance ?? 0;
          const dPerf = item.desktop?.performance ?? 0;
          // Keep records that are not total failures
          if (mPerf > 0 || dPerf > 0) {
            records.push(item);
          }
        } catch (err) {}
      }
      siteHistory[site.slug] = records;
    } catch (e) {
      console.warn(`Could not fetch history for ${site.name}:`, e);
      siteHistory[site.slug] = [];
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

  function generateSmoothPath(points) {
    if (points.length === 0) return "";
    if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
    if (points.length === 2) return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;

    let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[Math.max(i - 1, 0)];
      const p1 = points[i];
      const p2 = points[i + 1];
      const p3 = points[Math.min(i + 2, points.length - 1)];

      const cp1x = p1.x + (p2.x - p0.x) / 6;
      const cp1y = p1.y + (p2.y - p0.y) / 6;
      const cp2x = p2.x - (p3.x - p1.x) / 6;
      const cp2y = p2.y - (p3.y - p1.y) / 6;

      d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
    }
    return d;
  }

  function renderTrendChart(slug, strategy, metricKey) {
    const rawHistory = siteHistory[slug] || [];
    const cfg = METRIC_CONFIG[metricKey] || METRIC_CONFIG.performance;

    // Filter points for active strategy & metric
    const dataPoints = [];
    rawHistory.forEach(item => {
      const stratObj = item[strategy];
      const val = parseMetricNumber(stratObj, metricKey);
      if (val !== null) {
        dataPoints.push({
          date: new Date(item.timestamp),
          value: val,
          raw: stratObj,
          item: item
        });
      }
    });

    // Also include latest.json point if not already in history
    const latestSite = siteData[slug];
    if (latestSite && latestSite[strategy]) {
      const latestVal = parseMetricNumber(latestSite[strategy], metricKey);
      if (latestVal !== null) {
        const latestDate = new Date(latestSite.timestamp);
        const exists = dataPoints.some(
          p => Math.abs(p.date.getTime() - latestDate.getTime()) < 60000
        );
        if (!exists) {
          dataPoints.push({
            date: latestDate,
            value: latestVal,
            raw: latestSite[strategy],
            item: latestSite
          });
        }
      }
    }

    // Sort chronologically
    dataPoints.sort((a, b) => a.date - b.date);

    if (dataPoints.length === 0) {
      return `
        <div class="psi-chart-empty">
          <div class="psi-chart-empty-icon">📈</div>
          <div class="psi-chart-empty-title">Accumulating Daily Trend Data</div>
          <div class="psi-chart-empty-desc">
            Automated Lighthouse audits run daily at 06:00 UTC. Historical tracking curves will appear after scheduled audits run.
          </div>
        </div>
      `;
    }

    // Compute stats
    const values = dataPoints.map(p => p.value);
    const currentVal = values[values.length - 1];
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const avgVal = values.reduce((sum, v) => sum + v, 0) / values.length;

    let trendDiff = 0;
    let trendIcon = "▬";
    let trendClass = "trend-flat";
    if (values.length >= 2) {
      trendDiff = currentVal - values[0];
      if (metricKey === "performance") {
        if (trendDiff > 0) {
          trendIcon = "▲ +" + Math.round(trendDiff);
          trendClass = "trend-up";
        } else if (trendDiff < 0) {
          trendIcon = "▼ " + Math.round(trendDiff);
          trendClass = "trend-down";
        } else {
          trendIcon = "▬ Steady";
        }
      } else {
        // For LCP/CLS, lower is better!
        if (trendDiff < 0) {
          trendIcon = "▲ " + trendDiff.toFixed(2) + " (faster)";
          trendClass = "trend-up";
        } else if (trendDiff > 0) {
          trendIcon = "▼ +" + trendDiff.toFixed(2) + " (slower)";
          trendClass = "trend-down";
        } else {
          trendIcon = "▬ Steady";
        }
      }
    }

    // SVG Chart Geometry
    const svgWidth = 740;
    const svgHeight = 220;
    const pad = { top: 25, right: 30, bottom: 40, left: 45 };
    const chartW = svgWidth - pad.left - pad.right;
    const chartH = svgHeight - pad.top - pad.bottom;

    let yMin = cfg.yMin !== undefined ? cfg.yMin : 0;
    let yMax = cfg.yMax !== undefined ? cfg.yMax : Math.max(1, maxVal * 1.25);
    if (yMax <= yMin) yMax = yMin + 10;

    const points = dataPoints.map((p, idx) => {
      const x =
        dataPoints.length === 1
          ? pad.left + chartW / 2
          : pad.left + (idx / (dataPoints.length - 1)) * chartW;
      const normalizedY = Math.max(0, Math.min(1, (p.value - yMin) / (yMax - yMin)));
      const y = pad.top + chartH - normalizedY * chartH;
      return { x, y, ...p };
    });

    const linePath = generateSmoothPath(points);
    const areaPath =
      points.length > 1
        ? `${linePath} L ${points[points.length - 1].x} ${pad.top + chartH} L ${points[0].x} ${pad.top + chartH} Z`
        : "";

    // Grid ticks (4 steps)
    const ticks = [];
    const numTicks = 4;
    for (let i = 0; i <= numTicks; i++) {
      const val = yMin + (i / numTicks) * (yMax - yMin);
      const y = pad.top + chartH - (i / numTicks) * chartH;
      ticks.push({ y, val });
    }

    return `
      <div class="psi-chart-stats">
        <div class="psi-stat-pill">
          <span class="psi-stat-label">Current:</span>
          <strong class="psi-stat-val ${cfg.getScoreClass(currentVal)}">${cfg.formatVal(currentVal)}</strong>
        </div>
        <div class="psi-stat-pill">
          <span class="psi-stat-label">Average:</span>
          <strong class="psi-stat-val">${cfg.formatVal(avgVal)}</strong>
        </div>
        <div class="psi-stat-pill">
          <span class="psi-stat-label">Best:</span>
          <strong class="psi-stat-val ${cfg.getScoreClass(metricKey === 'performance' ? maxVal : minVal)}">${cfg.formatVal(metricKey === 'performance' ? maxVal : minVal)}</strong>
        </div>
        <div class="psi-stat-pill">
          <span class="psi-stat-label">Trend:</span>
          <strong class="psi-stat-val ${trendClass}">${trendIcon}</strong>
        </div>
      </div>

      <div class="psi-chart-svg-wrapper">
        <svg class="psi-trend-svg" viewBox="0 0 ${svgWidth} ${svgHeight}" preserveAspectRatio="none">
          <defs>
            <linearGradient id="psiChartGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--psi-accent)" stop-opacity="0.35"/>
              <stop offset="100%" stop-color="var(--psi-accent)" stop-opacity="0.01"/>
            </linearGradient>
          </defs>

          <!-- Grid lines & Y-axis labels -->
          ${ticks.map(t => `
            <line class="psi-chart-grid" x1="${pad.left}" y1="${t.y}" x2="${pad.left + chartW}" y2="${t.y}"></line>
            <text class="psi-chart-axis-label" x="${pad.left - 8}" y="${t.y + 4}" text-anchor="end">
              ${metricKey === "performance" ? Math.round(t.val) : t.val.toFixed(1)}
            </text>
          `).join("")}

          <!-- Underfill Area -->
          ${areaPath ? `<path class="psi-chart-area" d="${areaPath}" fill="url(#psiChartGrad)"></path>` : ""}

          <!-- Main Curve -->
          <path class="psi-chart-line" d="${linePath}"></path>

          <!-- Interactive Points -->
          ${points.map((p, idx) => `
            <g class="psi-chart-point-group"
               data-point-date="${p.date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}"
               data-point-time="${p.date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}"
               data-point-val="${cfg.formatVal(p.value)}"
               data-point-perf="${p.raw.performance || 'N/A'}"
               data-point-lcp="${p.raw.coreWebVitals?.largestContentfulPaint || 'N/A'}"
               data-point-fcp="${p.raw.coreWebVitals?.firstContentfulPaint || 'N/A'}"
               data-point-cls="${p.raw.coreWebVitals?.cumulativeLayoutShift || 'N/A'}">
              <circle class="psi-chart-dot-ring" cx="${p.x}" cy="${p.y}" r="8"></circle>
              <circle class="psi-chart-dot" cx="${p.x}" cy="${p.y}" r="4.5"></circle>
            </g>
          `).join("")}

          <!-- X-Axis Dates -->
          ${points.map((p, idx) => {
            // Show every point if <= 6 points, otherwise step
            const step = Math.ceil(points.length / 6);
            if (idx % step !== 0 && idx !== points.length - 1) return "";
            const dateStr = p.date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
            return `
              <text class="psi-chart-date-label" x="${p.x}" y="${pad.top + chartH + 20}" text-anchor="middle">
                ${dateStr}
              </text>
            `;
          }).join("")}
        </svg>

        <!-- Floating Interactive Tooltip -->
        <div id="psi-chart-tooltip" class="psi-chart-tooltip" style="display: none;"></div>
      </div>
    `;
  }

  function renderDashboard() {
    const container = ensureContainer();
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

        <!-- Historical Performance Trend Section -->
        <div class="psi-history-section">
          <div class="psi-history-header">
            <div>
              <h3 class="psi-history-title">📈 Performance Trend & Trajectory</h3>
              <p class="psi-history-subtitle">Historical daily Lighthouse and Core Web Vitals progression</p>
            </div>

            <!-- Metric Selector Tabs -->
            <div class="psi-metric-tabs">
              <button class="psi-metric-btn ${currentMetric === 'performance' ? 'active' : ''}" data-metric="performance">
                ⚡ Score
              </button>
              <button class="psi-metric-btn ${currentMetric === 'lcp' ? 'active' : ''}" data-metric="lcp">
                ⏱️ LCP
              </button>
              <button class="psi-metric-btn ${currentMetric === 'cls' ? 'active' : ''}" data-metric="cls">
                📐 CLS
              </button>
              <button class="psi-metric-btn ${currentMetric === 'fcp' ? 'active' : ''}" data-metric="fcp">
                🎨 FCP
              </button>
            </div>
          </div>

          <div class="psi-chart-container">
            ${renderTrendChart(currentSite.slug, currentStrategy, currentMetric)}
          </div>
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

    // Event Listeners: Site Tabs
    container.querySelectorAll('[data-site-idx]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentSiteIndex = parseInt(btn.getAttribute('data-site-idx'), 10);
        renderDashboard();
      });
    });

    // Event Listeners: Device Strategy Switcher
    container.querySelectorAll('[data-strategy]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentStrategy = btn.getAttribute('data-strategy');
        renderDashboard();
      });
    });

    // Event Listeners: Metric Switcher
    container.querySelectorAll('[data-metric]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentMetric = btn.getAttribute('data-metric');
        renderDashboard();
      });
    });

    // Event Listeners: Chart Point Hover Tooltips
    const tooltip = document.getElementById("psi-chart-tooltip");
    const chartWrapper = container.querySelector(".psi-chart-svg-wrapper");

    if (tooltip && chartWrapper) {
      container.querySelectorAll('.psi-chart-point-group').forEach(grp => {
        grp.addEventListener('mouseenter', e => {
          const date = grp.getAttribute('data-point-date');
          const time = grp.getAttribute('data-point-time');
          const val = grp.getAttribute('data-point-val');
          const perf = grp.getAttribute('data-point-perf');
          const lcp = grp.getAttribute('data-point-lcp');
          const fcp = grp.getAttribute('data-point-fcp');
          const cls = grp.getAttribute('data-point-cls');

          tooltip.innerHTML = `
            <div class="psi-tip-date">${date} (${time})</div>
            <div class="psi-tip-main">${METRIC_CONFIG[currentMetric].name}: <strong>${val}</strong></div>
            <div class="psi-tip-row"><span>Performance:</span> <strong>${perf}</strong></div>
            <div class="psi-tip-row"><span>LCP:</span> <strong>${lcp}</strong></div>
            <div class="psi-tip-row"><span>FCP:</span> <strong>${fcp}</strong></div>
            <div class="psi-tip-row"><span>CLS:</span> <strong>${cls}</strong></div>
          `;
          tooltip.style.display = 'block';
        });

        grp.addEventListener('mousemove', e => {
          const rect = chartWrapper.getBoundingClientRect();
          let x = e.clientX - rect.left;
          let y = e.clientY - rect.top - 120;
          if (x > rect.width - 160) x = rect.width - 160;
          if (x < 10) x = 10;
          if (y < 10) y = 10;

          tooltip.style.left = `${x}px`;
          tooltip.style.top = `${y}px`;
        });

        grp.addEventListener('mouseleave', () => {
          tooltip.style.display = 'none';
        });
      });
    }
  }

  function ensureContainer() {
    let container = document.getElementById("pagespeed-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "pagespeed-container";
      container.className = "container";
      const footer = document.querySelector("footer");
      if (footer && footer.parentNode) {
        footer.parentNode.insertBefore(container, footer);
      } else {
        const target = document.querySelector("main") || document.body;
        target.appendChild(container);
      }
    }
    return container;
  }

  async function init() {
    ensureContainer();

    // Load latest data and history for all monitored sites in parallel
    await Promise.all([
      ...SITES.map(fetchSiteData),
      ...SITES.map(fetchSiteHistory)
    ]);

    // Fallback: If siteData[slug] has 0 performance, but siteHistory[slug] has valid audits, use the latest from history!
    SITES.forEach(site => {
      const current = siteData[site.slug];
      const mScore = current?.mobile?.performance || 0;
      const dScore = current?.desktop?.performance || 0;
      if (mScore === 0 && dScore === 0) {
        const hist = siteHistory[site.slug] || [];
        if (hist.length > 0) {
          siteData[site.slug] = hist[hist.length - 1];
        }
      }
    });

    renderDashboard();

    // Re-inject if Svelte/Sapper re-renders layout or changes routes
    if (window.MutationObserver) {
      let debounceTimer;
      const observer = new MutationObserver(() => {
        if (!document.getElementById("pagespeed-container")) {
          clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => {
            renderDashboard();
          }, 100);
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
