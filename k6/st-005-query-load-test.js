import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // 逐步升载
    { duration: '5m', target: 50 },   // 稳定负载
    { duration: '2m', target: 80 },   // 提升压力
    { duration: '2m', target: 0 },    // 收尾
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000'],
  },
};

const BASE_URL = 'http://localhost:8080';

export default function () {

  // =========================
  // 1️⃣ 登录获取 token
  // =========================
  let loginRes = http.post(`${BASE_URL}/loginApi`,
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

  let token = loginRes.json('token');

  let headers = {
    Authorization: token || ''
  };

  // =========================
  // 2️⃣ 用户分页查询
  // =========================
  let userRes = http.get(`${BASE_URL}/sysUser/page?page=1&size=10`, {
    headers
  });

  check(userRes, {
    'user page ok': (r) => r.status === 200,
  });

  // =========================
  // 3️⃣ 组织树
  // =========================
  let orgRes = http.get(`${BASE_URL}/hrOrganization/page?page=1&size=10`, {
    headers
  });

  check(orgRes, {
    'org page ok': (r) => r.status === 200,
  });

  // =========================
  // 4️⃣ 角色分页
  // =========================
  let roleRes = http.get(`${BASE_URL}/sysRole/page?page=1&size=10`, {
    headers
  });

  check(roleRes, {
    'role page ok': (r) => r.status === 200,
  });

  // =========================
  // 5️⃣ 组织树结构接口
  // =========================
  let treeRes = http.get(`${BASE_URL}/common/org/tree`, {
    headers
  });

  check(treeRes, {
    'tree ok': (r) => r.status === 200,
  });

  sleep(1);
}