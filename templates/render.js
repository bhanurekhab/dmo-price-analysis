// Format year labels: replace hyphens with en dashes for AER style
function enDash(s) { return String(s).replace(/-/g, '–'); }
// Format signed values with en dash for negative
function fmtPct(v) { const n = Number(v); return (n < 0 ? '–' + Math.abs(n).toFixed(1) : n > 0 ? '+' + n.toFixed(1) : n.toFixed(1)) + '%'; }

// Read CSS custom properties for chart colours
const cs = getComputedStyle(document.documentElement);
DATA.colors = ['--c1','--c2','--c3','--c4','--c5'].map(v => cs.getPropertyValue(v).trim());

const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
Chart.defaults.color = isDark ? '#d1d5db' : '#374151';
Chart.defaults.borderColor = isDark ? '#3b4255' : '#e2e6ec';
Chart.defaults.font.family = "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.position = 'bottom';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyle = 'rect';
Chart.defaults.plugins.legend.labels.padding = 14;

// Findings
const findingsEl = document.getElementById('findings');
DATA.findings.forEach(f => {
  findingsEl.innerHTML += `<div class="finding"><strong>${f.title}</strong><p>${f.detail}</p></div>`;
});

// Price chart — nominal/real toggle state
let currentTab = 'residential';
let currentPriceMode = 'nominal';

let priceChart;
function buildPriceChart(type, mode) {
  const isRes = type === 'residential';
  const isReal = mode === 'real';
  const nomSrc = isRes ? DATA.residential : DATA.small_business;
  const realSrc = isRes ? DATA.residentialReal : DATA.smallBusinessReal;
  const src = isReal ? realSrc : nomSrc;
  const labels = (isRes ? DATA.resYears : DATA.sbYears).map(enDash);
  const datasets = DATA.zones.map((z, i) => ({
    label: DATA.zoneShort[i] + ' (' + DATA.states[z] + ')',
    data: src[z],
    borderColor: DATA.colors[i],
    backgroundColor: DATA.colors[i] + '18',
    borderWidth: 2,
    pointRadius: 4,
    pointHoverRadius: 6,
    tension: 0.15
  }));
  if (priceChart) priceChart.destroy();
  priceChart = new Chart(document.getElementById('priceChart'), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: {
          title: { display: true, text: isReal ? 'Annual price (2019–20 $)' : 'Annual price ($)' },
          ticks: { callback: v => '$' + v.toLocaleString() }
        }
      },
      plugins: {
        tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString() } }
      }
    }
  });

  // Update chart title and source
  const label = isRes ? 'Residential' : 'Small business';
  const yearRange = isRes ? '2019–20 to 2026–27' : '2022–23 to 2026–27';
  const suffix = isReal ? ', real (2019–20 $)' : '';
  document.getElementById('priceChartTitle').textContent = label + ' DMO prices by zone, ' + yearRange + ' ( $/year' + suffix + ')';
  document.getElementById('priceChartSource').textContent = isReal
    ? 'Data: AER DMO Final Determinations, flat rate tariff. CPI-adjusted to 2019–20 dollars (ABS cat. 6401.0).'
    : 'Data: AER DMO Final Determinations, flat rate tariff, nominal prices inclusive of GST.';
}

function switchTab(type) {
  currentTab = type;
  // Update tab row 1 buttons (Residential / Small business)
  const tabBtns = document.querySelectorAll('.tab-row:first-of-type .tab-btn');
  tabBtns.forEach(b => b.classList.remove('active'));
  tabBtns[type === 'residential' ? 0 : 1].classList.add('active');
  const isRes = type === 'residential';
  buildPriceChart(type, currentPriceMode);
  // Update tables
  buildPriceTable(
    currentPriceMode === 'real' ? (isRes ? DATA.residentialReal : DATA.smallBusinessReal) : (isRes ? DATA.residential : DATA.small_business),
    isRes ? 'priceTableRes' : 'priceTableSB',
    isRes ? DATA.resYears : DATA.sbYears
  );
  document.getElementById('priceTableRes').style.display = isRes ? '' : 'none';
  document.getElementById('resTableHeading').style.display = isRes ? '' : 'none';
  document.getElementById('priceTableSB').style.display = isRes ? 'none' : '';
  document.getElementById('sbTableHeading').style.display = isRes ? 'none' : '';
  const sbNote = document.getElementById('sbNote');
  if (sbNote) sbNote.style.display = isRes ? 'none' : '';
}

function switchPriceMode(mode) {
  currentPriceMode = mode;
  document.getElementById('nominalBtn').classList.toggle('active', mode === 'nominal');
  document.getElementById('realBtn').classList.toggle('active', mode === 'real');
  const isRes = currentTab === 'residential';
  buildPriceChart(currentTab, mode);
  // Rebuild the visible table with real or nominal data
  const isReal = mode === 'real';
  const resSrc = isReal ? DATA.residentialReal : DATA.residential;
  const sbSrc = isReal ? DATA.smallBusinessReal : DATA.small_business;
  buildPriceTable(resSrc, 'priceTableRes', DATA.resYears);
  buildPriceTable(sbSrc, 'priceTableSB', DATA.sbYears);
  // Update table headings
  const suffix = isReal ? ', real (2019–20 $)' : '';
  document.getElementById('resTableHeading').textContent = 'Residential prices ($/year' + suffix + ')';
  document.getElementById('sbTableHeading').textContent = 'Small business prices ($/year' + suffix + '; 10,000 kWh usage, 10,027 kWh in 2023–24)';
}

function buildPriceTable(src, elId, years) {
  let h = '<table><thead><tr><th>Zone</th><th>State</th>';
  years.forEach(y => h += `<th class="num">${enDash(y)}</th>`);
  h += '</tr></thead><tbody>';
  DATA.zones.forEach(z => {
    h += `<tr><td>${z}</td><td>${DATA.states[z]}</td>`;
    src[z].forEach(v => h += `<td class="num">$${v.toLocaleString()}</td>`);
    h += '</tr>';
  });
  h += '</tbody></table>';
  document.getElementById(elId).innerHTML = h;
}
buildPriceTable(DATA.residential, 'priceTableRes', DATA.resYears);
buildPriceTable(DATA.small_business, 'priceTableSB', DATA.sbYears);

// YoY chart
const yoyYears = DATA.resYears.slice(1);
const yoyLabelsEn = yoyYears.map(enDash);
const yoyData = DATA.zones.map(z => {
  const p = DATA.residential[z];
  return p.slice(1).map((v, i) => ((v - p[i]) / p[i] * 100).toFixed(1));
});

new Chart(document.getElementById('yoyChart'), {
  type: 'bar',
  data: {
    labels: yoyLabelsEn,
    datasets: DATA.zones.map((z, i) => ({
      label: DATA.zoneShort[i],
      data: yoyData[i].map(Number),
      backgroundColor: DATA.colors[i] + 'cc',
      borderColor: DATA.colors[i],
      borderWidth: 1
    }))
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    scales: {
      y: { title: { display: true, text: 'Change (%)' }, ticks: { callback: v => v + '%' } }
    },
    plugins: {
      tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%' } }
    }
  }
});

// YoY table
{
  let h = '<table><thead><tr><th>Zone</th>';
  yoyYears.forEach(y => h += `<th class="num">${enDash(y)}</th>`);
  h += '</tr></thead><tbody>';
  DATA.zones.forEach((z, i) => {
    h += `<tr><td>${z}</td>`;
    yoyData[i].forEach(v => {
      const cls = v > 0 ? 'positive' : v < 0 ? 'negative' : '';
      h += `<td class="num ${cls}">${fmtPct(v)}</td>`;
    });
    h += '</tr>';
  });
  h += '</tbody></table>';
  document.getElementById('yoyTable').innerHTML = h;
}

// Cost component range chart (horizontal bar showing min-max for DMO 8)
const compNames = ['Wholesale','Network','Environmental','Retail'];
const compKeys = ['wholesale','network','environmental','retail'];
const cc = DATA.costRanges["2026-27"];

new Chart(document.getElementById('costRangeChart'), {
  type: 'bar',
  data: {
    labels: compNames,
    datasets: [
      {
        label: 'Minimum share',
        data: compKeys.map(k => cc[k].min),
        backgroundColor: DATA.colors.slice(0,4).map(c => c + '66'),
        borderColor: DATA.colors.slice(0,4),
        borderWidth: 1
      },
      {
        label: 'Range above minimum',
        data: compKeys.map(k => cc[k].max - cc[k].min),
        backgroundColor: DATA.colors.slice(0,4).map(c => c + 'cc'),
        borderColor: DATA.colors.slice(0,4),
        borderWidth: 1
      }
    ]
  },
  options: {
    indexAxis: 'y',
    responsive: true, maintainAspectRatio: false,
    scales: {
      x: { stacked: true, title: { display: true, text: 'Share of DMO price (%)' }, ticks: { callback: v => v + '%' }, max: 60 },
      y: { stacked: true }
    },
    plugins: {
      legend: { display: true, labels: { generateLabels: function(chart) { return [{text: 'Minimum share', fillStyle: chart.data.datasets[0].backgroundColor[0], strokeStyle: chart.data.datasets[0].borderColor[0], lineWidth: 1, fontColor: Chart.defaults.color}, {text: 'Range to maximum', fillStyle: chart.data.datasets[1].backgroundColor[0], strokeStyle: chart.data.datasets[1].borderColor[0], lineWidth: 1, fontColor: Chart.defaults.color}]; } } },
      tooltip: {
        callbacks: {
          label: function(ctx) {
            const k = compKeys[ctx.dataIndex];
            return compNames[ctx.dataIndex] + ': ' + cc[k].min + '–' + cc[k].max + '%';
          }
        }
      }
    }
  }
});

// Cost table (ranges)
{
  let h = '<table><thead><tr><th>Component</th><th class="num">Minimum</th><th class="num">Maximum</th></tr></thead><tbody>';
  compKeys.forEach((k, i) => {
    h += `<tr><td>${compNames[i]}</td>`;
    h += `<td class="num">${cc[k].min}%</td>`;
    h += `<td class="num">${cc[k].max}%</td>`;
    h += '</tr>';
  });
  h += '</tbody></table>';
  document.getElementById('costTable').innerHTML = h;
}

// Standing offer chart
const soYears = DATA.standingOffer.years;

new Chart(document.getElementById('standingOfferChart'), {
  type: 'bar',
  data: {
    labels: soYears,
    datasets: [
      { label: 'Residential', data: DATA.standingOffer.residential.counts, backgroundColor: DATA.colors[0]+'cc', borderColor: DATA.colors[0], borderWidth: 1, yAxisID: 'y' },
      { label: 'Small business', data: DATA.standingOffer.small_business.counts, backgroundColor: DATA.colors[1]+'cc', borderColor: DATA.colors[1], borderWidth: 1, yAxisID: 'y' },
      { label: 'Residential share (%)', data: DATA.standingOffer.residential.shares, type: 'line', borderColor: DATA.colors[0], backgroundColor: 'transparent', borderWidth: 2, pointRadius: 5, yAxisID: 'y1' },
      { label: 'SB share (%)', data: DATA.standingOffer.small_business.shares, type: 'line', borderColor: DATA.colors[1], backgroundColor: 'transparent', borderWidth: 2, borderDash: [5,3], pointRadius: 5, yAxisID: 'y1' }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    scales: {
      y: { position: 'left', title: { display: true, text: 'Customers' }, ticks: { callback: v => (v/1000).toFixed(0) + 'k' } },
      y1: { position: 'right', title: { display: true, text: 'Share of customers (%)' }, ticks: { callback: v => v + '%' }, grid: { drawOnChartArea: false }, min: 0, max: 25 }
    }
  }
});

// Standing offer table
{
  let h = '<table><thead><tr><th>Year</th><th class="num">Residential</th><th class="num">Share</th><th class="num">Small business</th><th class="num">Share</th></tr></thead><tbody>';
  soYears.forEach((y, i) => {
    h += `<tr><td>${enDash(y)}</td>`;
    h += `<td class="num">${DATA.standingOffer.residential.counts[i].toLocaleString()}</td>`;
    h += `<td class="num">${DATA.standingOffer.residential.shares[i].toFixed(1)}%</td>`;
    h += `<td class="num">${DATA.standingOffer.small_business.counts[i].toLocaleString()}</td>`;
    h += `<td class="num">${DATA.standingOffer.small_business.shares[i].toFixed(1)}%</td>`;
    h += '</tr>';
  });
  h += '</tbody></table>';
  document.getElementById('soTable').innerHTML = h;
}

buildPriceChart('residential', 'nominal');
