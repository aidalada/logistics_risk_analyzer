import http from "k6/http";
import { check, fail, sleep } from "k6";

const baseUrl = __ENV.BASE_URL || "http://localhost:8080";
const authEmail = __ENV.AUTH_EMAIL || "capacity_tester@example.com";
const authPassword = __ENV.AUTH_PASSWORD || "capacityPass123!";

export const options = {
  stages: [
    { duration: "2m", target: 10 },
    { duration: "3m", target: 30 },
    { duration: "3m", target: 60 },
    { duration: "2m", target: 100 },
    { duration: "2m", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"], // error rate below 5%
    http_req_duration: ["p(95)<800"], // p95 latency below 800ms
    checks: ["rate>0.95"],
  },
};

function authToken() {
  const payload = `username=${encodeURIComponent(authEmail)}&password=${encodeURIComponent(authPassword)}`;
  const res = http.post(`${baseUrl}/api/auth/login`, payload, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  check(res, { "auth status is 200": (r) => r.status === 200 });
  if (res.status !== 200) return "";
  const data = res.json();
  return data.access_token || "";
}

function registerUserIfNeeded() {
  const res = http.post(
    `${baseUrl}/api/auth/register`,
    JSON.stringify({
      email: authEmail,
      password: authPassword,
      role: "client",
    }),
    { headers: { "Content-Type": "application/json" } }
  );
  // 200 = registered, 400 = already exists (acceptable)
  check(res, { "register status is 200 or 400": (r) => r.status === 200 || r.status === 400 });
}

export function setup() {
  let token = authToken();
  if (!token) {
    registerUserIfNeeded();
    token = authToken();
  }
  if (!token) {
    fail("Unable to authenticate test user. Check auth-service and credentials.");
  }
  return { token };
}

export default function (data) {
  const headers = { Authorization: `Bearer ${data.token}` };

  const r1 = http.get(`${baseUrl}/api/orders/health`);
  check(r1, { "orders health 200": (r) => r.status === 200 });

  const r2 = http.get(`${baseUrl}/api/products/categories`);
  check(r2, { "categories 200": (r) => r.status === 200 });

  const r3 = http.get(`${baseUrl}/api/orders/`, { headers });
  check(r3, { "list orders != 5xx": (r) => r.status < 500 });

  sleep(1);
}
