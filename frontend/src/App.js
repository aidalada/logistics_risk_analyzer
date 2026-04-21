import React, { createContext, useContext, useMemo, useState } from 'react';
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import './App.css';
import Register from './Register';

const PRODUCT_CATEGORIES = [
  'moveis_escritorio',
  'fashion_roupa_masculina',
  'telefonia_fixa',
  'audio',
  'casa_conforto',
  'other',
];
const PAYMENT_METHODS = ['credit_card', 'boleto', 'voucher', 'debit_card'];
const ORDER_STATUSES = ['New', 'Processing', 'In Transit', 'Delivered', 'Canceled'];

const AuthContext = createContext(null);

const decodeJwtPayload = (token) => {
  if (!token) {
    return null;
  }
  try {
    const base64Payload = token.split('.')[1];
    const normalized = base64Payload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
    return JSON.parse(window.atob(padded));
  } catch (_error) {
    return null;
  }
};

const getUserRoleFromToken = (token) => {
  const payload = decodeJwtPayload(token);
  return payload?.role || 'client';
};

const hasRoleAccess = (role, allowedRoles) => allowedRoles.includes(role);

const getStatusBadgeClass = (status) => {
  switch (status) {
    case 'New':
      return 'status-new';
    case 'Processing':
      return 'status-processing';
    case 'In Transit':
      return 'status-in-transit';
    case 'Delivered':
      return 'status-delivered';
    case 'Canceled':
      return 'status-canceled';
    default:
      return 'status-new';
  }
};

const clampPct = (value) => Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));

const AnalyticsDonut = ({ summary }) => {
  const total = Number(summary?.total_orders) || 0;
  const high = Number(summary?.high_risk_count) || 0;
  const inTransit = Number(summary?.in_transit_count) || 0;
  const delivered = Number(summary?.delivered_count) || 0;
  const other = Math.max(0, total - high - inTransit - delivered);

  const segments = [
    { key: 'high', label: 'High risk', value: high, className: 'seg-high' },
    { key: 'inTransit', label: 'In transit', value: inTransit, className: 'seg-transit' },
    { key: 'delivered', label: 'Delivered', value: delivered, className: 'seg-delivered' },
    { key: 'other', label: 'Other', value: other, className: 'seg-other' },
  ].filter((s) => s.value > 0);

  const size = 168;
  const stroke = 16;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;

  let offset = 0;
  const normalized = total > 0 ? segments : [{ key: 'none', label: 'No data', value: 1, className: 'seg-none' }];

  return (
    <div className="analytics-chart">
      <div className="donut-wrap">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            className="donut-track"
            fill="none"
            strokeWidth={stroke}
          />
          {normalized.map((seg) => {
            const pct = total > 0 ? seg.value / total : 1;
            const len = c * pct;
            const dasharray = `${len} ${c - len}`;
            const dashoffset = -offset;
            offset += len;
            return (
              <circle
                key={seg.key}
                cx={size / 2}
                cy={size / 2}
                r={r}
                className={`donut-seg ${seg.className}`}
                fill="none"
                strokeWidth={stroke}
                strokeDasharray={dasharray}
                strokeDashoffset={dashoffset}
                strokeLinecap="butt"
              />
            );
          })}
          <circle cx={size / 2} cy={size / 2} r={r - stroke / 2} className="donut-hole" />
          <text x="50%" y="48%" textAnchor="middle" className="donut-total">
            {total}
          </text>
          <text x="50%" y="62%" textAnchor="middle" className="donut-subtitle">
            orders
          </text>
        </svg>
      </div>

      <div className="donut-legend">
        {[
          { key: 'high', label: 'High risk', value: high, className: 'seg-high' },
          { key: 'inTransit', label: 'In transit', value: inTransit, className: 'seg-transit' },
          { key: 'delivered', label: 'Delivered', value: delivered, className: 'seg-delivered' },
          { key: 'other', label: 'Other', value: other, className: 'seg-other' },
        ].map((item) => {
          const pct = total ? clampPct(Math.round((item.value / total) * 100)) : 0;
          return (
            <div key={item.key} className="legend-item">
              <span className={`legend-dot ${item.className}`} />
              <span className="legend-label">{item.label}</span>
              <span className="legend-value">{item.value}</span>
              <span className="legend-pct">{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const ProtectedRoute = ({ allowedRoles, children }) => {
  const { role } = useAuth();
  const location = useLocation();
  if (!hasRoleAccess(role, allowedRoles)) {
    return <Navigate to="/orders" replace state={{ accessDenied: true, from: location.pathname }} />;
  }
  return children;
};

const useAuth = () => useContext(AuthContext);

function AppLayout() {
  const { token, role, setToken, setRole } = useAuth();
  const [apiResponse, setApiResponse] = useState('');
  const [orders, setOrders] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [mlResult, setMlResult] = useState(null);
  const [mlLoading, setMlLoading] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [analyticsSummary, setAnalyticsSummary] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  const [mlForm, setMlForm] = useState({
    price: '',
    freight_value: '',
    product_weight_g: '',
    product_length_cm: '',
    product_height_cm: '',
    product_width_cm: '',
    product_category_name: 'other',
    customer_lat: '',
    customer_lng: '',
    seller_lat: '',
    seller_lng: '',
    purchase_timestamp: '',
    estimated_delivery_date: '',
    order_purchase_timestamp: '',
    order_approved_at: '',
    customer_state: '',
    payment_type: 'credit_card',
    payment_installments: 1,
  });

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  // ML is integrated into backend /orders now.

  const callApi = async (endpoint, method = 'GET', body = null, isForm = false) => {
    try {
      const headers = {};
      if (!isForm) {
        headers['Content-Type'] = 'application/json';
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }
      } else {
        headers['Content-Type'] = 'application/x-www-form-urlencoded';
      }

      const options = { method, headers };
      if (body) {
        options.body = isForm ? body : JSON.stringify(body);
      }

      const response = await fetch(`${API_URL}${endpoint}`, options);
      const data = await response.json();

      if (response.ok) {
        setApiResponse(JSON.stringify(data, null, 2));
        return data;
      }
      setApiResponse(`Ошибка ${response.status}: \n${JSON.stringify(data, null, 2)}`);
      return null;
    } catch (error) {
      setApiResponse(`Ошибка сети: ${error.message}`);
      return null;
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const data = await callApi('/login', 'POST', formData, true);
    if (data && data.access_token) {
      setToken(data.access_token);
      setRole(getUserRoleFromToken(data.access_token));
      localStorage.setItem('token', data.access_token);
      setApiResponse('');
      navigate('/orders', { replace: true });
    }
  };

  const handleLogout = () => {
    setToken('');
    setRole('client');
    localStorage.removeItem('token');
    setApiResponse('');
    setMlResult(null);
    setOrders([]);
    navigate('/orders', { replace: true });
  };

  const loadOrders = async () => {
    setOrdersLoading(true);
    try {
      const data = await callApi('/orders', 'GET');
      if (Array.isArray(data)) {
        setOrders(data);
      }
    } finally {
      setOrdersLoading(false);
    }
  };

  const handleMlInputChange = (event) => {
    const { name, value } = event.target;
    setMlForm((prev) => ({ ...prev, [name]: value }));
  };

  const buildMlPayload = () => ({
    price: Number(mlForm.price),
    freight_value: Number(mlForm.freight_value),
    product_weight_g: Number(mlForm.product_weight_g),
    product_length_cm: Number(mlForm.product_length_cm),
    product_height_cm: Number(mlForm.product_height_cm),
    product_width_cm: Number(mlForm.product_width_cm),
    product_category_name: mlForm.product_category_name,
    customer_lat: Number(mlForm.customer_lat),
    customer_lng: Number(mlForm.customer_lng),
    seller_lat: Number(mlForm.seller_lat),
    seller_lng: Number(mlForm.seller_lng),
    purchase_timestamp: new Date(mlForm.purchase_timestamp).toISOString(),
    estimated_delivery_date: new Date(mlForm.estimated_delivery_date).toISOString(),
    order_purchase_timestamp: new Date(mlForm.order_purchase_timestamp).toISOString(),
    order_approved_at: mlForm.order_approved_at
      ? new Date(mlForm.order_approved_at).toISOString()
      : null,
    customer_state: mlForm.customer_state.toUpperCase(),
    payment_type: mlForm.payment_type,
    payment_installments: Number(mlForm.payment_installments),
  });

  const getRiskTone = (valuePercent, riskKey) => {
    if (riskKey === 'cancel_risk_percent') {
      if (valuePercent < 1.5) {
        return { className: 'risk-good', label: 'Низкий' };
      }
      if (valuePercent <= 10) {
        return { className: 'risk-medium', label: 'Средний' };
      }
      return { className: 'risk-high', label: 'Высокий' };
    }

    if (valuePercent < 15) {
      return { className: 'risk-good', label: 'Низкий' };
    }
    if (valuePercent < 40) {
      return { className: 'risk-medium', label: 'Средний' };
    }
    return { className: 'risk-high', label: 'Высокий' };
  };

  const handlePredictOnly = async (event) => {
    event.preventDefault();
    setMlLoading(true);
    setMlResult(null);

    try {
      const payload = buildMlPayload();
      const predicted = await callApi('/ml/predict', 'POST', {
        price: payload.price,
        freight_value: payload.freight_value,
        weight_g: payload.product_weight_g,
        length_cm: payload.product_length_cm,
        height_cm: payload.product_height_cm,
        width_cm: payload.product_width_cm,
        category: payload.product_category_name,
        payment_type: payload.payment_type,
        installments: payload.payment_installments,
        customer_lat: payload.customer_lat,
        customer_lng: payload.customer_lng,
        seller_lat: payload.seller_lat,
        seller_lng: payload.seller_lng,
        purchase_timestamp: payload.purchase_timestamp,
        estimated_delivery_date: payload.estimated_delivery_date,
        order_approved_at: payload.order_approved_at,
        customer_state: payload.customer_state,
      });
      if (predicted) {
        setMlResult(predicted);
      }
    } catch (error) {
      setApiResponse(`Ошибка сети ML: ${error.message}`);
    } finally {
      setMlLoading(false);
    }
  };

  const handleCreateOrder = async (event) => {
    event.preventDefault();
    setMlLoading(true);
    setMlResult(null);
    try {
      const payload = buildMlPayload();
      const created = await callApi('/orders', 'POST', {
        price: payload.price,
        freight_value: payload.freight_value,
        weight_g: payload.product_weight_g,
        length_cm: payload.product_length_cm,
        height_cm: payload.product_height_cm,
        width_cm: payload.product_width_cm,
        category: payload.product_category_name,
        payment_type: payload.payment_type,
        installments: payload.payment_installments,
        customer_lat: payload.customer_lat,
        customer_lng: payload.customer_lng,
        seller_lat: payload.seller_lat,
        seller_lng: payload.seller_lng,
        purchase_timestamp: payload.purchase_timestamp,
        estimated_delivery_date: payload.estimated_delivery_date,
        order_approved_at: payload.order_approved_at,
        customer_state: payload.customer_state,
      });
      if (created) {
        navigate('/orders');
        await loadOrders();
      }
    } finally {
      setMlLoading(false);
    }
  };

  const handleUpdateOrderStatus = async (orderId, nextStatus) => {
    const updated = await callApi(`/orders/${orderId}/status`, 'PATCH', { status: nextStatus });
    if (!updated) {
      return;
    }
    setOrders((prev) => prev.map((o) => (o.id === orderId ? { ...o, status: updated.status } : o)));
    setSelectedOrder((prev) => (prev?.id === orderId ? { ...prev, status: updated.status } : prev));
  };

  const loadAnalyticsSummary = async () => {
    setAnalyticsLoading(true);
    try {
      const data = await callApi('/analytics/summary', 'GET');
      if (data) {
        setAnalyticsSummary(data);
      }
    } finally {
      setAnalyticsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="login-screen">
        <div className="login-card">
          <div className="login-header">
            <h2>Logistics SRE</h2>
            <p>Платформа управления рисками</p>
          </div>
          <form onSubmit={handleLogin} className="login-form">
            <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <input type="password" placeholder="Пароль" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <button type="submit" className="btn-primary">Войти в систему</button>
          </form>
          {apiResponse && <p className="auth-error">{apiResponse}</p>}
          <p className="auth-switch">
            Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header className="header">
        <div className="logo-area">
          <div className="status-dot"></div>
          <h1>Logistics Dashboard</h1>
        </div>
        <button onClick={handleLogout} className="btn-logout">Выйти</button>
      </header>

      <div className="main-layout">
        <aside className="sidebar">
          <nav className="nav-tabs">
            <button onClick={() => navigate('/orders')} className={location.pathname === '/orders' ? 'active' : ''}>📦 Мои заказы</button>
            {hasRoleAccess(role, ['operator', 'admin']) && (
              <>
                <button onClick={() => navigate('/ml-prediction')} className={location.pathname === '/ml-prediction' ? 'active' : ''}>⚡ ML прогноз</button>
                <button onClick={() => navigate('/create-order')} className={location.pathname === '/create-order' ? 'active' : ''}>🧾 Создать заказ</button>
              </>
            )}
            {role === 'admin' && (
              <button onClick={() => navigate('/analytics')} className={location.pathname === '/analytics' ? 'active' : ''}>📊 Аналитика (Админ)</button>
            )}
            <button onClick={() => navigate('/profile')} className={location.pathname === '/profile' ? 'active' : ''}>👤 Профиль</button>
          </nav>
        </aside>

        <main className="content">
          <div className="content-card">
            <Routes>
              <Route path="/" element={<Navigate to="/orders" replace />} />
              <Route
                path="/orders"
                element={(
              <section className="fade-in">
                <h2>Список ваших заказов</h2>
                <p className="subtitle">Мониторинг текущих логистических операций.</p>
                {location.state?.accessDenied && (
                  <p className="subtitle">Нет доступа</p>
                )}
                <button className="btn-action" onClick={loadOrders} disabled={ordersLoading}>
                  {ordersLoading ? 'Загрузка...' : 'Загрузить базу заказов'}
                </button>
                {orders.length > 0 && (
                  <div className="orders-table-container">
                    <table className="orders-table">
                      <thead>
                        <tr>
                          <th>ID</th>
                          <th>Category</th>
                          <th>Payment</th>
                          <th>Статус</th>
                          {hasRoleAccess(role, ['operator', 'admin']) && <th>Действия</th>}
                          <th>Дата</th>
                          {hasRoleAccess(role, ['operator', 'admin']) && <th>Risk Level</th>}
                        </tr>
                      </thead>
                      <tbody>
                        {orders.map((order) => (
                          <tr key={order.id} className="orders-row" onClick={() => setSelectedOrder(order)}>
                            <td>{order.id}</td>
                            <td>{order.category ?? '-'}</td>
                            <td>{order.payment_type ?? '-'}</td>
                            <td>
                              <span className={`status-badge ${getStatusBadgeClass(order.status)}`}>
                                {order.status}
                              </span>
                            </td>
                            {hasRoleAccess(role, ['operator', 'admin']) && (
                              <td onClick={(e) => e.stopPropagation()}>
                                <div className="status-actions">
                                  <select
                                    value={order.status}
                                    onChange={(e) => handleUpdateOrderStatus(order.id, e.target.value)}
                                    aria-label={`Change status for order ${order.id}`}
                                  >
                                    {ORDER_STATUSES.map((s) => (
                                      <option key={s} value={s}>
                                        {s}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                              </td>
                            )}
                            <td>{new Date(order.created_at).toLocaleString()}</td>
                            {hasRoleAccess(role, ['operator', 'admin']) && <td>{order.risk_level ?? '-'}</td>}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {selectedOrder && (
                  <div className="modal-overlay" onClick={() => setSelectedOrder(null)}>
                    <div className="modal-card" onClick={(e) => e.stopPropagation()}>
                      <div className="modal-header">
                        <h3>Заказ #{selectedOrder.id}</h3>
                        <button className="modal-close" onClick={() => setSelectedOrder(null)}>×</button>
                      </div>
                      <p className="subtitle" style={{ marginBottom: '12px' }}>
                        Статус:{' '}
                        <span className={`status-badge ${getStatusBadgeClass(selectedOrder.status)}`}>
                          {selectedOrder.status}
                        </span>{' '}
                        · Risk: <b>{selectedOrder.risk_level ?? '-'}</b>
                      </p>
                      {hasRoleAccess(role, ['operator', 'admin']) ? (
                        <div style={{ display: 'grid', gap: '12px' }}>
                          {[
                            { key: 'delay_probability', title: 'Delay risk', value: selectedOrder.delay_probability },
                            { key: 'damage_probability', title: 'Damage risk', value: selectedOrder.damage_probability },
                            { key: 'cancel_probability', title: 'Cancel risk', value: selectedOrder.cancel_probability },
                          ].map((item) => {
                            const pct = Math.round((Number(item.value) || 0) * 100);
                            const width = Math.max(0, Math.min(100, pct));
                            return (
                              <div key={item.key} className="risk-card">
                                <h3>{item.title}</h3>
                                <p className="risk-percent">{pct}%</p>
                                <div className="risk-progress">
                                  <div className="risk-progress-fill" style={{ width: `${width}%`, backgroundColor: 'var(--primary)' }} />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="subtitle">Детальная ML-аналитика доступна только operator/admin.</p>
                      )}
                    </div>
                  </div>
                )}
              </section>
                )}
              />

              <Route
                path="/ml-prediction"
                element={(
                  <ProtectedRoute allowedRoles={['operator', 'admin']}>
              <section className="fade-in">
                <h2>ML прогноз (без сохранения)</h2>
                <p className="subtitle">Показывает 3 риска (delay/damage/cancel) без сохранения заказа в базе.</p>
                <form className="form-group vertical" onSubmit={handlePredictOnly}>
                  <div className="input-row">
                    <input type="number" name="price" step="0.01" min="0" placeholder="Price" value={mlForm.price} onChange={handleMlInputChange} required />
                    <input type="number" name="freight_value" step="0.01" min="0" placeholder="Freight value" value={mlForm.freight_value} onChange={handleMlInputChange} required />
                  </div>

                  <input type="number" name="product_weight_g" step="1" min="0" placeholder="Product weight (g)" value={mlForm.product_weight_g} onChange={handleMlInputChange} required />

                  <div className="input-row">
                    <input type="number" name="product_length_cm" step="0.01" min="0.01" placeholder="Product length (cm)" value={mlForm.product_length_cm} onChange={handleMlInputChange} required />
                    <input type="number" name="product_height_cm" step="0.01" min="0.01" placeholder="Product height (cm)" value={mlForm.product_height_cm} onChange={handleMlInputChange} required />
                    <input type="number" name="product_width_cm" step="0.01" min="0.01" placeholder="Product width (cm)" value={mlForm.product_width_cm} onChange={handleMlInputChange} required />
                  </div>

                  <select name="product_category_name" value={mlForm.product_category_name} onChange={handleMlInputChange} required>
                    {PRODUCT_CATEGORIES.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>

                  <div className="input-row">
                    <select name="payment_type" value={mlForm.payment_type} onChange={handleMlInputChange} required>
                      {PAYMENT_METHODS.map((method) => (
                        <option key={method} value={method}>
                          {method}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      name="payment_installments"
                      min="1"
                      max="24"
                      step="1"
                      placeholder="Payment installments"
                      value={mlForm.payment_installments}
                      onChange={handleMlInputChange}
                      required
                    />
                  </div>

                  <div className="input-row">
                    <input type="number" name="customer_lat" step="0.000001" min="-90" max="90" placeholder="Customer latitude" value={mlForm.customer_lat} onChange={handleMlInputChange} required />
                    <input type="number" name="customer_lng" step="0.000001" min="-180" max="180" placeholder="Customer longitude" value={mlForm.customer_lng} onChange={handleMlInputChange} required />
                  </div>

                  <div className="input-row">
                    <input type="number" name="seller_lat" step="0.000001" min="-90" max="90" placeholder="Seller latitude" value={mlForm.seller_lat} onChange={handleMlInputChange} required />
                    <input type="number" name="seller_lng" step="0.000001" min="-180" max="180" placeholder="Seller longitude" value={mlForm.seller_lng} onChange={handleMlInputChange} required />
                  </div>

                  <div className="input-row">
                    <label className="field-label">
                      Purchase timestamp
                      <input type="datetime-local" name="purchase_timestamp" value={mlForm.purchase_timestamp} onChange={handleMlInputChange} required />
                    </label>
                    <label className="field-label">
                      Estimated delivery date
                      <input type="datetime-local" name="estimated_delivery_date" value={mlForm.estimated_delivery_date} onChange={handleMlInputChange} required />
                    </label>
                  </div>

                  <div className="input-row">
                    <label className="field-label">
                      Order purchase timestamp
                      <input
                        type="datetime-local"
                        name="order_purchase_timestamp"
                        value={mlForm.order_purchase_timestamp}
                        onChange={handleMlInputChange}
                        required
                      />
                    </label>
                    <label className="field-label">
                      Order approved at (optional)
                      <input
                        type="datetime-local"
                        name="order_approved_at"
                        value={mlForm.order_approved_at}
                        onChange={handleMlInputChange}
                      />
                    </label>
                  </div>

                  <input type="text" name="customer_state" minLength="2" maxLength="2" placeholder="Customer state (e.g. SP)" value={mlForm.customer_state} onChange={handleMlInputChange} required />

                  <button className="btn-action pulse" type="submit" disabled={mlLoading}>
                    {mlLoading ? 'Выполняем прогноз...' : 'Рассчитать риски'}
                  </button>
                </form>

                {mlResult && (
                  <div className="risk-grid">
                    {[
                      { key: 'delay_probability', title: 'Риск задержки', value: (Number(mlResult.delay_probability) || 0) * 100 },
                      { key: 'damage_probability', title: 'Риск повреждения', value: (Number(mlResult.damage_probability) || 0) * 100 },
                      { key: 'cancel_probability', title: 'Риск отмены заказа', value: (Number(mlResult.cancel_probability) || 0) * 100 },
                    ].map((riskItem) => {
                      const tone = getRiskTone(Number(riskItem.value), riskItem.key);
                      return (
                        <div key={riskItem.key} className={`risk-card ${tone.className}`}>
                          <h3>{riskItem.title}</h3>
                          <p className="risk-percent">{Number(riskItem.value).toFixed(2)}%</p>
                          <p className="risk-label">{tone.label} риск</p>
                          <div className="risk-progress">
                            <div
                              className={`risk-progress-fill ${tone.className}`}
                              style={{ width: `${Math.max(0, Math.min(100, Number(riskItem.value)))}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
                  </ProtectedRoute>
                )}
              />

              <Route
                path="/create-order"
                element={(
                  <ProtectedRoute allowedRoles={['operator', 'admin']}>
                    <section className="fade-in">
                      <h2>Создать заказ</h2>
                      <p className="subtitle">Сохраняет заказ в БД и фиксирует риски (3 модели).</p>
                      <form className="form-group vertical" onSubmit={handleCreateOrder}>
                        <div className="input-row">
                          <input type="number" name="price" step="0.01" min="0" placeholder="Price" value={mlForm.price} onChange={handleMlInputChange} required />
                          <input type="number" name="freight_value" step="0.01" min="0" placeholder="Freight value" value={mlForm.freight_value} onChange={handleMlInputChange} required />
                        </div>

                        <input type="number" name="product_weight_g" step="1" min="0" placeholder="Product weight (g)" value={mlForm.product_weight_g} onChange={handleMlInputChange} required />

                        <div className="input-row">
                          <input type="number" name="product_length_cm" step="0.01" min="0.01" placeholder="Product length (cm)" value={mlForm.product_length_cm} onChange={handleMlInputChange} required />
                          <input type="number" name="product_height_cm" step="0.01" min="0.01" placeholder="Product height (cm)" value={mlForm.product_height_cm} onChange={handleMlInputChange} required />
                          <input type="number" name="product_width_cm" step="0.01" min="0.01" placeholder="Product width (cm)" value={mlForm.product_width_cm} onChange={handleMlInputChange} required />
                        </div>

                        <select name="product_category_name" value={mlForm.product_category_name} onChange={handleMlInputChange} required>
                          {PRODUCT_CATEGORIES.map((category) => (
                            <option key={category} value={category}>
                              {category}
                            </option>
                          ))}
                        </select>

                        <div className="input-row">
                          <select name="payment_type" value={mlForm.payment_type} onChange={handleMlInputChange} required>
                            {PAYMENT_METHODS.map((method) => (
                              <option key={method} value={method}>
                                {method}
                              </option>
                            ))}
                          </select>
                          <input
                            type="number"
                            name="payment_installments"
                            min="1"
                            max="24"
                            step="1"
                            placeholder="Payment installments"
                            value={mlForm.payment_installments}
                            onChange={handleMlInputChange}
                            required
                          />
                        </div>

                        <div className="input-row">
                          <input type="number" name="customer_lat" step="0.000001" min="-90" max="90" placeholder="Customer latitude" value={mlForm.customer_lat} onChange={handleMlInputChange} required />
                          <input type="number" name="customer_lng" step="0.000001" min="-180" max="180" placeholder="Customer longitude" value={mlForm.customer_lng} onChange={handleMlInputChange} required />
                        </div>

                        <div className="input-row">
                          <input type="number" name="seller_lat" step="0.000001" min="-90" max="90" placeholder="Seller latitude" value={mlForm.seller_lat} onChange={handleMlInputChange} required />
                          <input type="number" name="seller_lng" step="0.000001" min="-180" max="180" placeholder="Seller longitude" value={mlForm.seller_lng} onChange={handleMlInputChange} required />
                        </div>

                        <div className="input-row">
                          <label className="field-label">
                            Purchase timestamp
                            <input type="datetime-local" name="purchase_timestamp" value={mlForm.purchase_timestamp} onChange={handleMlInputChange} required />
                          </label>
                          <label className="field-label">
                            Estimated delivery date
                            <input type="datetime-local" name="estimated_delivery_date" value={mlForm.estimated_delivery_date} onChange={handleMlInputChange} required />
                          </label>
                        </div>

                        <div className="input-row">
                          <label className="field-label">
                            Order purchase timestamp
                            <input
                              type="datetime-local"
                              name="order_purchase_timestamp"
                              value={mlForm.order_purchase_timestamp}
                              onChange={handleMlInputChange}
                              required
                            />
                          </label>
                          <label className="field-label">
                            Order approved at (optional)
                            <input
                              type="datetime-local"
                              name="order_approved_at"
                              value={mlForm.order_approved_at}
                              onChange={handleMlInputChange}
                            />
                          </label>
                        </div>

                        <input type="text" name="customer_state" minLength="2" maxLength="2" placeholder="Customer state (e.g. SP)" value={mlForm.customer_state} onChange={handleMlInputChange} required />

                        <button className="btn-action pulse" type="submit" disabled={mlLoading}>
                          {mlLoading ? 'Сохраняем...' : 'Создать заказ'}
                        </button>
                      </form>
                    </section>
                  </ProtectedRoute>
                )}
              />

              <Route
                path="/analytics"
                element={(
                  <ProtectedRoute allowedRoles={['admin']}>
              <section className="fade-in">
                <h2>Сводная статистика</h2>
                <p className="subtitle">Доступ только для администраторов с уровнем доступа SRE.</p>
                <button className="btn-action" onClick={loadAnalyticsSummary} disabled={analyticsLoading}>
                  {analyticsLoading ? 'Собираем данные...' : 'Сгенерировать отчет'}
                </button>

                {analyticsSummary && (
                  <>
                    <AnalyticsDonut summary={analyticsSummary} />
                    <div className="analytics-grid">
                      {(() => {
                        const total = Number(analyticsSummary.total_orders) || 0;
                        const safePct = (value) => {
                          if (!total) return 0;
                          return Math.max(0, Math.min(100, Math.round((Number(value) / total) * 100)));
                        };

                        return (
                          <>
                            <div className="metric-card">
                              <div className="metric-title">Total orders</div>
                              <div className="metric-value">{total}</div>
                              <div className="metric-bar">
                                <div className="metric-bar-fill bar-primary" style={{ width: '100%' }} />
                              </div>
                            </div>

                            <div className="metric-card">
                              <div className="metric-title">High risk orders</div>
                              <div className="metric-value">{analyticsSummary.high_risk_count}</div>
                              <div className="metric-bar">
                                <div
                                  className="metric-bar-fill bar-danger"
                                  style={{ width: `${safePct(analyticsSummary.high_risk_count)}%` }}
                                />
                              </div>
                            </div>

                            <div className="metric-card">
                              <div className="metric-title">In transit</div>
                              <div className="metric-value">{analyticsSummary.in_transit_count}</div>
                              <div className="metric-bar">
                                <div
                                  className="metric-bar-fill bar-purple"
                                  style={{ width: `${safePct(analyticsSummary.in_transit_count)}%` }}
                                />
                              </div>
                            </div>

                            <div className="metric-card">
                              <div className="metric-title">Delivered</div>
                              <div className="metric-value">{analyticsSummary.delivered_count}</div>
                              <div className="metric-bar">
                                <div
                                  className="metric-bar-fill bar-success"
                                  style={{ width: `${safePct(analyticsSummary.delivered_count)}%` }}
                                />
                              </div>
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  </>
                )}
              </section>
                  </ProtectedRoute>
                )}
              />

              <Route
                path="/profile"
                element={(
              <section className="fade-in">
                <h2>Профиль оператора</h2>
                <p className="subtitle">Проверка токена и прав доступа.</p>
                <button className="btn-action" onClick={() => callApi('/users/me', 'GET')}>Проверить JWT Token</button>
              </section>
                )}
              />
            </Routes>
          </div>

          <div className="api-response-container">
            <div className="terminal-header">
              <span>Terminal: API Response</span>
            </div>
            <div className="terminal-box">
              <pre>{location.pathname === '/orders' && role === 'client' ? 'Для клиентов raw JSON скрыт. Используйте таблицу заказов.' : (apiResponse || 'Ожидание входящих данных...')}</pre>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [role, setRole] = useState(getUserRoleFromToken(localStorage.getItem('token') || ''));

  const authState = useMemo(
    () => ({ token, role, setToken, setRole }),
    [token, role]
  );

  return (
    <AuthContext.Provider value={authState}>
      <BrowserRouter>
        <Routes>
          <Route
            path="/register"
            element={
              token ? (
                <Navigate to="/orders" replace />
              ) : (
                <Register
                  onRegisterSuccess={({ accessToken, userRole }) => {
                    setToken(accessToken);
                    setRole(userRole);
                    localStorage.setItem('token', accessToken);
                  }}
                />
              )
            }
          />
          <Route path="/*" element={<AppLayout />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

export default App;