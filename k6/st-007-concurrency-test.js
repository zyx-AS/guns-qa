import http from 'k6/http';
import { check, sleep } from 'k6';

// =========================
// ST-007 并发测试
// =========================
export let options = {

  vus: 80,              // 固定并发
  duration: '10m',      // 持续运行

  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.01'],
  }
};

// =========================
// 并发执行逻辑
// =========================
export default function () {

  // 1️⃣ 登录
  let loginRes = http.post('http://localhost:8080/loginApi',
    JSON.stringify({
      username: 'test',
      password: '123456'
    }),
    {
      headers: { 'Content-Type': 'application/json' }
    }
  );

  check(loginRes, {
    'login success': (r) => r.status === 200,
  });

  let token = 'mock-token-123456';

  let headers = {
    headers: {
      Authorization: token
    }
  };

  // 2️⃣ 并发访问核心接口
  http.get('http://localhost:8080/userIndexInfo', headers);
  http.get('http://localhost:8080/sysUser/page?page=1&size=10', headers);
  http.get('http://localhost:8080/sysRole/page?page=1&size=10', headers);
  http.get('http://localhost:8080/common/org/tree', headers);

  sleep(1);
}