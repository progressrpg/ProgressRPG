// src/config.js
let API_BASE_URL;
const envApiBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (envApiBaseUrl) {
  API_BASE_URL = envApiBaseUrl;
} else if (window.location.hostname === 'localhost') {
  API_BASE_URL = 'http://localhost:8000';
} else {
  API_BASE_URL = window.location.origin;
}

API_BASE_URL = API_BASE_URL.replace(/\/api\/v1\/?$/i, '');
API_BASE_URL = API_BASE_URL.replace(/\/$/, '');

export { API_BASE_URL };
