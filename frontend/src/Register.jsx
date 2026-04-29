import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api/auth';

const ROLE_OPTIONS = [
  { value: 'client', label: 'Client' },
  { value: 'operator', label: 'Operator' },
  { value: 'admin', label: 'Admin' },
];

function Register({ onRegisterSuccess }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('client');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Пароли не совпадают');
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role }),
      });
      const responseText = await response.text();
      let data;
      try {
        data = responseText ? JSON.parse(responseText) : {};
      } catch (_parseError) {
        data = { detail: responseText || 'Invalid server response' };
      }

      if (!response.ok) {
        setError(data?.detail || 'Не удалось зарегистрироваться');
        return;
      }

      onRegisterSuccess({
        accessToken: data.access_token,
        userRole: role,
      });
      navigate('/orders', { replace: true });
    } catch (_error) {
      setError('Ошибка сети. Попробуйте снова');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-header">
          <h2>Logistics SRE</h2>
          <p>Создание нового аккаунта</p>
        </div>
        <form onSubmit={handleSubmit} className="login-form">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={8}
          />
          <input
            type="password"
            placeholder="Подтвердите пароль"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
            minLength={8}
          />
          <select value={role} onChange={(event) => setRole(event.target.value)} required>
            {ROLE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? 'Создаем аккаунт...' : 'Зарегистрироваться'}
          </button>
        </form>
        {error && <p className="auth-error">{error}</p>}
        <p className="auth-switch">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </div>
    </div>
  );
}

export default Register;
