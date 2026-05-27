import http from 'k6/http';
import { check, sleep } from 'k6';

// =========================
// ST-006 压力测试（递增模型）
// =========================
export let options = {
  stages: [
    { duration: '30s', target: 50 },    // 轻负载
    { duration: '30s', target: 100 },   // 中负载
    { duration: '30s', target: 150 },   // 高负载
    { duration: '30s', target: 200 },   // 压力上升
    { duration: '30s', target: 250 },   // 极限压力
    { duration: '30s', target: 0 },     // 下降收敛
  ],

  thresholds: {
    http_req_duration: ['p(95)<3000'],  // 压力测试放宽
    http_req_failed: ['rate<0.1'],      // 失败率允许10%
  },
};

// =========================
// 压测主流程（真实用户链路）
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

  let loginOk = check(loginRes, {
    'login success': (r) => r.status === 200,
  });

  // token（mock固定）
  let token = 'mock-token-123456';

  let headers = {
    headers: {
      Authorization: token
    }
  };

  // 2️⃣ 首页接口
  http.get('http://localhost:8080/userIndexInfo', headers);

  // 3️⃣ 查询链路（核心压力点）
  http.get('http://localhost:8080/sysUser/page?page=1&size=10', headers);
  http.get('http://localhost:8080/sysRole/page?page=1&size=10', headers);
  http.get('http://localhost:8080/hrOrganization/page?page=1&size=10', headers);
  http.get('http://localhost:8080/common/org/tree', headers);

  sleep(1);
}