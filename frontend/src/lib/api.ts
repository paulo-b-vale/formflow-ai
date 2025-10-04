import axios from 'axios';

// Use the environment variable for the API URL, defaulting to localhost for development
// In Docker, this should be set to http://app:8000 or http://host.docker.internal:8002
const baseURL = process.env.NEXT_PUBLIC_API_URL || 
               (typeof window !== 'undefined' ? 'http://localhost:8002' : 'http://localhost:8002');

const api = axios.create({
  baseURL,
});

// Interceptor to add the auth token to every request if it exists
api.interceptors.request.use(config => {
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