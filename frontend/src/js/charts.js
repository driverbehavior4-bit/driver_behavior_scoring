// charts.js — Chart.js builders
const _charts = {};

function destroyChart(id) {
  if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
}

function scoreColor(score) {
  if (score >= 70) return '#16a34a';
  if (score >= 40) return '#d97706';
  return '#dc2626';
}

function renderRiskDoughnut(canvasId, data) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  _charts[canvasId] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Low Risk', 'Moderate Risk', 'High Risk'],
      datasets: [{ data: [data.low||0, data.moderate||0, data.high||0],
        backgroundColor: ['#16a34a','#d97706','#dc2626'], borderWidth: 2, borderColor: '#fff' }]
    },
    options: { plugins: { legend: { position:'bottom' } }, cutout: '65%', responsive: true }
  });
}

function renderTopRiskBar(canvasId, drivers) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const names  = drivers.map(d => d.driver_name || d.driver_id);
  const scores = drivers.map(d => d.overall_score);
  _charts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{ label: 'Overall Score', data: scores,
        backgroundColor: scores.map(s => scoreColor(s)), borderRadius: 4 }]
    },
    options: { indexAxis: 'y', responsive: true,
      plugins: { legend: { display: false } },
      scales: { x: { min: 0, max: 100 } } }
  });
}

function renderScoreTrend(canvasId, trendData) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const labels = trendData.map(t => t.trip_date || t.trip_id);
  const values = trendData.map(t => t.trip_safety_score);
  _charts[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{ label: 'Trip Safety Score', data: values, borderColor: '#2563eb',
        backgroundColor: 'rgba(37,99,235,0.1)', fill: true, tension: 0.3,
        pointRadius: 4, pointBackgroundColor: values.map(v => scoreColor(v)) }]
    },
    options: { responsive: true, plugins: { legend: { display: false } },
      scales: { y: { min: 0, max: 100 } } }
  });
}

function renderFleetDistribution(canvasId, buckets) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const labels = Object.keys(buckets||{});
  const values = Object.values(buckets||{});
  _charts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Trips', data: values,
        backgroundColor: labels.map(l => {
          const mid = (parseInt(l)+parseInt(l.split('-')[1]))/2;
          return scoreColor(mid);
        }), borderRadius: 4 }]
    },
    options: { responsive: true, plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } } }
  });
}

function renderHarshEvents(canvasId, data) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const names  = data.map(d => d.name || d.driver_id);
  const values = data.map(d => d.total_harsh_events);
  _charts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{ label: 'Harsh Events', data: values, backgroundColor: '#f59e0b', borderRadius: 4 }]
    },
    options: { indexAxis: 'y', responsive: true,
      plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
  });
}

function renderDailyTrips(canvasId, daily) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  _charts[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: daily.map(d => d.date),
      datasets: [{ label: 'Trips', data: daily.map(d => d.count), borderColor: '#2563eb',
        backgroundColor: 'rgba(37,99,235,0.1)', fill: true, tension: 0.2 }]
    },
    options: { responsive: true, plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } } }
  });
}
