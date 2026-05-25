const fs = require("fs");

const inputPath = process.argv[2] || "perf-tests/k6/result.json";
const outputPath = process.argv[3] || "perf-tests/k6/analysis.json";

const raw = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const m = raw.metrics || {};

const avgRt = (m.http_req_duration && m.http_req_duration.values && m.http_req_duration.values.avg) || null;
const p95 = (m.http_req_duration && m.http_req_duration.values && m.http_req_duration.values["p(95)"]) || null;
const tps = (m.http_reqs && m.http_reqs.values && m.http_reqs.values.rate) || null;
const errorRate = (m.http_req_failed && m.http_req_failed.values && m.http_req_failed.values.rate) || null;
const failed = (m.http_req_failed && m.http_req_failed.values && m.http_req_failed.values.fails) || 0;
const passes = (m.http_req_failed && m.http_req_failed.values && m.http_req_failed.values.passes) || 0;

const pass = p95 !== null && errorRate !== null && p95 < 800 && errorRate < 0.01;

const result = {
  pass,
  verdict: pass ? "PASS" : "FAIL",
  avg_rt_ms: avgRt,
  p95_ms: p95,
  tps,
  error_rate: errorRate,
  http_req_failed: {
    fails: failed,
    passes,
  },
  tested_at: new Date().toISOString(),
};

fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
