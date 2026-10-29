// api.js — API service layer
const API_BASE = 'http://localhost:8000';

async function apiRequest(endpoint, method = 'GET', body = null) {
  const headers = { 'Content-Type': 'application/json', ...auth.getAuthHeader() };
  const opts = { method, headers };
  if (body !== null && method !== 'GET') opts.body = JSON.stringify(body);
  let response;
  try {
    response = await fetch(API_BASE + endpoint, opts);
  } catch (e) {
    throw new Error('Cannot reach server. Is the backend running on port 8000?');
  }
  if (response.status === 401) { auth.handleUnauthorized(); throw new Error('Unauthorized'); }
  if (!response.ok) {
    let detail = `Server error ${response.status}`;
    try { const b = await response.json(); detail = b.detail || b.message || detail; } catch {}
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

const api = {
  // Auth
  async login(username, password) {
    const res = await fetch(API_BASE + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) { const b = await res.json().catch(()=>({})); throw new Error(b.detail || 'Login failed'); }
    return res.json();
  },

  // Analytics
  getDashboard:        () => apiRequest('/analytics/dashboard'),
  getFleetAnalytics:   () => apiRequest('/analytics/fleet'),
  getHighRiskDrivers:  () => apiRequest('/analytics/high-risk-drivers'),
  getDriverTrend:      (id) => apiRequest(`/analytics/driver/${id}/trend`),

  // Drivers
  getDrivers:          () => apiRequest('/drivers'),
  getDriver:           (id) => apiRequest(`/drivers/${id}`),
  getDriverTrips:      (id) => apiRequest(`/drivers/${id}/trips`),
  createDriver:        (d) => apiRequest('/drivers', 'POST', d),

  // Scores
  getDriverScore:      (id) => apiRequest(`/scores/driver/${id}`),

  // Trips
  getTrips:            (limit=20) => apiRequest(`/trips?limit=${limit}`),
  createTrip:          (d) => apiRequest('/trips', 'POST', d),

  // Coaching
  getCoaching:         () => apiRequest('/coaching'),
  createCoaching:      (d) => apiRequest('/coaching', 'POST', d),
  updateCoaching:      (id, d) => apiRequest(`/coaching/${id}`, 'PUT', d),
  getCoachingByDriver: (id) => apiRequest(`/coaching/driver/${id}`),
};
