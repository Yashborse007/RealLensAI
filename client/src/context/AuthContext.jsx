import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

/**
 * Centralized API base URL — reads from Vite env var or falls back to the
 * Vite dev proxy path so the proxy handles cross-origin in development.
 */
const API_BASE =
  import.meta.env.DEV
    ? '/api'
    : import.meta.env.VITE_API_BASE_URL || '/api';

const getAuthRequestError = (error, action) => {
  if (!error.response) {
    return `Cannot connect to the RealLens API while trying to ${action}. Start the backend on port 5000 and keep the frontend dev server running.`;
  }

  return (
    error.response.data?.error ||
    error.response.data?.message ||
    `Unable to ${action}. Please try again.`
  );
};

/**
 * Dedicated auth Axios instance so auth calls always hit the right backend
 * and carry the correct Authorization header without polluting defaults.
 */
const authClient = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,
  timeout: 15000,
});

// Attach Bearer token on every outgoing auth request if available
authClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('reallens_auth_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('reallens_auth_token') || null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Keep the global axios default header in sync so other api.js calls work too
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('reallens_auth_token', token);
    } else {
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('reallens_auth_token');
    }
  }, [token]);

  // Verify stored token on initial mount
  useEffect(() => {
    const loadUser = async () => {
      const storedToken = localStorage.getItem('reallens_auth_token');
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        const res = await authClient.get('/auth/me');

        if (res.data?.success) {
          setUser(res.data.user);
          setToken(storedToken);
        } else {
          logout();
        }
      } catch (err) {
        const status = err.response?.status;
        if (status === 401 || status === 403) {
          // Token expired or invalid — clear it
          logout();
        } else {
          setUser(null);
          setAuthError(
            'Unable to verify your session. Check the server connection and sign in again.',
          );
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadUser();
  }, []);

  const login = async (email, password) => {
    setAuthError(null);
    try {
      const res = await authClient.post('/auth/login', {
        email: email.trim().toLowerCase(),
        password,
      });
      if (res.data?.success) {
        const { token: newToken, user: newUser } = res.data;
        setToken(newToken);
        setUser(newUser);
        return { success: true, user: newUser };
      }
      const msg = res.data?.error || 'Login failed. Please check credentials.';
      setAuthError(msg);
      return { success: false, error: msg };
    } catch (err) {
      const message = getAuthRequestError(err, 'sign in');
      setAuthError(message);
      return { success: false, error: message };
    }
  };

  const register = async (name, email, password) => {
    setAuthError(null);
    try {
      const res = await authClient.post('/auth/register', {
        name: name.trim(),
        email: email.trim().toLowerCase(),
        password,
      });
      if (res.data?.success) {
        const { token: newToken, user: newUser } = res.data;
        setToken(newToken);
        setUser(newUser);
        return { success: true, user: newUser };
      }
      const msg = res.data?.error || 'Registration failed.';
      setAuthError(msg);
      return { success: false, error: msg };
    } catch (err) {
      const message = getAuthRequestError(err, 'register');
      setAuthError(message);
      return { success: false, error: message };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    setAuthError(null);
    localStorage.removeItem('reallens_auth_token');
    localStorage.removeItem('reallens_user_name');
    localStorage.removeItem('reallens_user_email');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        authError,
        login,
        register,
        logout,
        setAuthError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
