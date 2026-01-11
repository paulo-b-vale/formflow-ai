import axios from 'axios';

// Use relative URLs to go through our Next.js API routes proxy
// The API routes in /pages/api/ will forward requests to the backend
const baseURL = '';

const api = axios.create({
  baseURL,
});

// Interceptor to add the auth token to every request if it exists
api.interceptors.request.use(config => {
  // Modify the URL to use our proxy routes
  // Add /api prefix to routes that need to be proxied
  if (config.url?.startsWith('/auth/') ||
      config.url?.startsWith('auth/') ||
      config.url?.startsWith('/users/') ||
      config.url?.startsWith('users/') ||
      config.url?.startsWith('/forms-management/') ||
      config.url?.startsWith('forms-management/') ||
      config.url?.startsWith('/analytics/') ||
      config.url?.startsWith('analytics/') ||
      config.url?.startsWith('/files/') ||
      config.url?.startsWith('files/') ||
      config.url?.startsWith('/enhanced_conversation/') ||
      config.url?.startsWith('enhanced_conversation/')) {
    // Only add /api prefix if it's not already there
    if (!config.url.startsWith('/api/')) {
      config.url = `/api${config.url}`;
    }
  }

  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
}, error => {
  return Promise.reject(error);
});

export default api;