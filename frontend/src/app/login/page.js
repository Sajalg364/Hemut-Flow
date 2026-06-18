'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { xhrRequest } from '@/lib/xhr';
import { API_URL } from '@/lib/constants';
import Link from 'next/link';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [form, setForm] = useState({ username: '', password: '' });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);

  const validate = () => {
    const errs = {};
    if (!form.username.trim()) errs.username = 'Username is required';
    if (!form.password) errs.password = 'Password is required';
    if (form.password && form.password.length < 6) errs.password = 'Password must be at least 6 characters';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    if (!validate()) return;

    setLoading(true);
    try {
      const { data } = await xhrRequest({
        method: 'POST',
        url: `${API_URL}/auth/login`,
        data: { username: form.username, password: form.password },
      });
      login(data.access_token, data.user);
      router.push('/chat');
    } catch (err) {
      setServerError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1 style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <img src="/logo.jpg" alt="Hemut Logo" style={{ width: '32px', height: '32px', borderRadius: '4px', marginRight: '12px' }} />
            Hemut
          </h1>
          <p>Logistics Collaboration Platform</p>
        </div>

        {serverError && (
          <div className="alert-error">
            ⚠️ {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="login-username">Username</label>
            <input
              id="login-username"
              type="text"
              className={`form-input ${errors.username ? 'error' : ''}`}
              placeholder="Enter your username"
              value={form.username}
              onChange={(e) => setForm(prev => ({ ...prev, username: e.target.value }))}
              autoComplete="username"
            />
            {errors.username && <div className="form-error">⚠ {errors.username}</div>}
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              className={`form-input ${errors.password ? 'error' : ''}`}
              placeholder="Enter your password"
              value={form.password}
              onChange={(e) => setForm(prev => ({ ...prev, password: e.target.value }))}
              autoComplete="current-password"
            />
            {errors.password && <div className="form-error">⚠ {errors.password}</div>}
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            id="login-submit"
          >
            {loading ? <><div className="spinner"></div> Signing in...</> : 'Sign In'}
          </button>
        </form>

        <div className="auth-footer">
          Don&apos;t have an account? <Link href="/register">Create one</Link>
        </div>
      </div>
    </div>
  );
}
