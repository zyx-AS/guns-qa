import http from 'k6/http';
import { check, sleep } from 'k6';

// =========================
// ST-008 稳定性测试
// =========================
export let options = {

  vus: 30,              // 中等并发（稳定性关键）
  duration: '30m',      // 长时间运行（核心）

  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.01'],
  }
};

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

  // 2️⃣ 长时间稳定访问
  http.get('http://localhost:8080/userIndexInfo', headers);
  http.get('http://localhost:8080/sysUser/page?page=1&size=10', headers);
  http.get('http://localhost:8080/sysRole/page?page=1&size=10', headers);
  http.get('http://localhost:8080/common/org/tree', headers);

  sleep(1);
}