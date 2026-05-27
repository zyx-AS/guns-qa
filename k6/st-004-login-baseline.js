import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 20 },   // 基线阶段（轻负载）
    { duration: '2m', target: 20 },   // 稳定运行
    { duration: '1m', target: 0 },    // 结束
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],        // 失败率 < 1%
    http_req_duration: ['p(95)<800'],      // P95 < 800ms
  },
};

const BASE_URL = 'http://localhost:8080';

export default function () {

  // =========================
  // 1️⃣ 登录接口
  // =========================
  let loginRes = http.post(`${BASE_URL}/loginApi`,
    JSON.stringify({
      username: 'test',
      password: '123456'
    }),
    {
      headers: {
        'Content-Type': 'application/json'
      }
    }
  );

  check(loginRes, {
    'login status is 200': (r) => r.status === 200,
  });

  let token = loginRes.json('token');

  // =========================
  // 2️⃣ 首页接口
  // =========================
  let indexRes = http.get(`${BASE_URL}/userIndexInfo`, {
    headers: {
      Authorization: token ? token : '',
    },
  });

  check(indexRes, {
    'index status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
