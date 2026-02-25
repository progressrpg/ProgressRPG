let API_BASE_URL;

if (window.location.hostname === 'localhost') {
  API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
} else {
  API_BASE_URL = `${window.location.protocol}//${window.location.hostname}`;
}

// Remove trailing slash
API_BASE_URL = API_BASE_URL.replace(/\/$/, '');

export { API_BASE_URL };
