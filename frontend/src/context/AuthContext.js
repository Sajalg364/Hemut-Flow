'use client';

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getToken, setToken, removeToken, getStoredUser, setStoredUser, clearAuth, getAuthHeaders } from '@/lib/auth';
import { xhrGet } from '@/lib/xhr';
import { API_URL } from '@/lib/constants';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check auth on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken();
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const { data } = await xhrGet(`${API_URL}/auth/me`, getAuthHeaders());
        setUser(data);
        setStoredUser(data);
        setIsAuthenticated(true);
      } catch {
        clearAuth();
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = useCallback((token, userData) => {
    setToken(token);
    setStoredUser(userData);
    setUser(userData);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    setIsAuthenticated(false);
    window.location.href = '/login';
  }, []);

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
