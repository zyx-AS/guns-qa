# ST-006 登录链路性能测试（基线压测）

## 执行方式

```bash
k6 run perf-tests/k6/st006_login_baseline.js --summary-export=perf-tests/k6/result.json
```

可选环境变量：

- `BASE_URL`：目标服务地址，默认 `http://127.0.0.1:8080`
- `LOGIN_USERNAME`：默认 `test`
- `LOGIN_PASSWORD`：默认 `123456`

## HTML 报告生成

```bash
npx k6-html-reporter perf-tests/k6/result.json --output perf-tests/k6/summary.html
```

## 指标说明

- `avg RT`：`http_req_duration.avg`，平均响应时间（ms）
- `P95`：`http_req_duration.p(95)`，95 分位响应时间（ms）
- `TPS`：`http_reqs.rate`，每秒请求数
- `error rate`：`http_req_failed.rate`
- 判定标准：
  - `P95 < 800ms`
  - `error rate < 1%`
