// auth.js — JWT session management
const TOKEN_KEY = 'fleet_token';
const USER_KEY  = 'fleet_user';

const auth = {
  getToken()           { return localStorage.getItem(TOKEN_KEY); },
  getUser()            { try { return JSON.parse(localStorage.getItem(USER_KEY)||'{}'); } catch { return {}; } },
  isLoggedIn()         { return !!this.getToken(); },
  getAuthHeader()      { return { 'Authorization': 'Bearer ' + this.getToken() }; },
  setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  checkAuth() {
    if (!this.isLoggedIn()) window.location.href = 'index.html';
  },
  checkAlreadyLoggedIn() {
    if (this.isLoggedIn()) window.location.href = 'dashboard.html';
  },
  handleUnauthorized() {
    this.clearSession();
    window.location.href = 'index.html';
  },
};
