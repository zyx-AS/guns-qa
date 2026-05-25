import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8080";
const USERNAME = __ENV.LOGIN_USERNAME || "test";
const PASSWORD = __ENV.LOGIN_PASSWORD || "123456";

export const options = {
  stages: [
    { duration: "30s", target: 10 },
    { duration: "60s", target: 50 },
    { duration: "60s", target: 100 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<800"],
  },
};

export default function () {
  const loginPayload = JSON.stringify({
    username: USERNAME,
    password: PASSWORD,
  });

  const loginRes = http.post(`${BASE_URL}/loginApi`, loginPayload, {
    headers: { "Content-Type": "application/json" },
    tags: { api: "loginApi" },
  });

  const loginOk = check(loginRes, {
    "login status is 200": (r) => r.status === 200,
    "login has token": (r) => {
      try {
        const body = r.json();
        return !!(body && (body.token || (body.data && body.data.token)));
      } catch (e) {
        return false;
      }
    },
  });

  let token = "";
  if (loginOk) {
    const body = loginRes.json();
    token = body.token || (body.data && body.data.token) || "";
  }

  const indexRes = http.get(`${BASE_URL}/userIndexInfo`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    tags: { api: "userIndexInfo" },
  });

  check(indexRes, {
    "userIndexInfo status is 200": (r) => r.status === 200,
  });

  sleep(1);
}
