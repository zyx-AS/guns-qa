# 测试文档索引

本目录保存每条测试的老师版 README，按测试类型分目录管理。

## 使用说明

- 模板与示例请参考 [`docs/testing/`](../../docs/testing/README.md)
- 新增测试文档前，建议先运行：
  - `powershell -ExecutionPolicy Bypass -File .\scripts\new-test-doc.ps1 ...`
  - 或 `bash scripts/new-test-doc.sh ...`
- 每次新增或修改测试时，请同步更新本索引和对应分类索引。

## 当前目录

- [unit/README.md](./unit/README.md)
  单元测试 README 索引。
- [integration/README.md](./integration/README.md)
  集成测试 README 索引。
- [system/README.md](./system/README.md)
  系统测试 README 索引。
- [performance/README.md](./performance/README.md)
  性能测试 README 索引。

## 当前已登记测试

| 测试编号 | 测试类型 | 标题 | README |
| --- | --- | --- | --- |
| `UT-core-security-001` | 单元测试 | BlackWhiteInterceptor 请求拦截校验测试 | [查看](./unit/UT-core-security-001/README.md) |
