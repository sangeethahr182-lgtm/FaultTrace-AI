const API_BASE = '/api';

export async function fetchOverview() {
  const res = await fetch(`${API_BASE}/dashboard/overview`);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function fetchFeeders() {
  const res = await fetch(`${API_BASE}/feeders`);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function fetchTopology(feederId) {
  const res = await fetch(`${API_BASE}/feeders/${feederId}/topology`);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function analyzeFault(feederId, lookbackMinutes = 30) {
  const res = await fetch(`${API_BASE}/faults/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feeder_id: feederId, lookback_minutes: lookbackMinutes })
  });
  if (!res.ok) throw new Error(`Fault analysis failed: ${res.status}`);
  return res.json();
}

export async function fetchRecentPredictions() {
  const res = await fetch(`${API_BASE}/faults/predictions`);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function generateRestorationPlan(predictionId, targetSectionId = null) {
  const res = await fetch(`${API_BASE}/restoration/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prediction_id: predictionId, target_section_id: targetSectionId })
  });
  if (!res.ok) throw new Error(`Plan generation failed: ${res.status}`);
  return res.json();
}

export async function fetchRestorationPlans() {
  const res = await fetch(`${API_BASE}/restoration/plans`);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function fetchWeather() {
  const res = await fetch(`${API_BASE}/weather`);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/analytics/metrics`);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function fetchTrends() {
  const res = await fetch(`${API_BASE}/analytics/trends`);
  if (!res.ok) throw new Error(`HTTP error ${res.status}`);
  return res.json();
}

export async function ingestEvent(eventData) {
  const res = await fetch(`${API_BASE}/events/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(eventData)
  });
  if (!res.ok) throw new Error(`Event ingestion failed: ${res.status}`);
  return res.json();
}

export async function uploadData(payload) {
  const res = await fetch(`${API_BASE}/data/upload`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}
