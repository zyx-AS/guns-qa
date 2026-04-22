# 测试文档规范

本目录用于统一维护 `guns-qa` 仓库中的测试文档模板、写作说明和示例。

## 目录说明

- [test-readme-template.md](./test-readme-template.md)
  统一的测试 README 模板，覆盖单元测试、集成测试、系统测试、性能测试四类场景。
- [examples/unit-example.md](./examples/unit-example.md)
  单元测试 README 示例。
- [examples/integration-example.md](./examples/integration-example.md)
  集成测试 README 示例。
- [examples/system-example.md](./examples/system-example.md)
  系统测试 README 示例。
- [examples/performance-example.md](./examples/performance-example.md)
  性能测试 README 示例。

## 编号约定

- 单元测试：`UT-模块-序号`
- 集成测试：`IT-链路-序号`
- 系统测试：`ST-场景-序号`
- 性能测试：`PT-场景-序号`

## 新增一条测试文档的推荐流程

1. 在 `guns-tests/src/test/` 下新增或修改测试代码。
2. 运行 `scripts/new-test-doc.ps1` 或 `scripts/new-test-doc.sh` 生成 README 骨架。
3. 按照 [test-readme-template.md](./test-readme-template.md) 补齐内容。
4. 参考 `examples/` 目录中的示例，调整成老师易读的正式表述。
5. 在 `guns-tests/docs/README.md` 和对应分类索引中登记该测试。
6. 提交前确认 `.github/workflows/validate-test-docs.yml` 能通过。

## 写作原则

- README 面向老师和项目成员阅读，不面向机器日志直接展示。
- `实际结果` 节要用自然语言概括本次执行结果，必要时补充 GitHub Actions run、Jira issue、artifact 名称。
- 原始 XML、长日志、截图、录屏等证据应放在 GitHub Actions artifacts、Jira 附件或其他归档位置，通过链接或名称引用。

## 与 GitHub / Jira 的分工

- GitHub 仓库负责保存模板、示例、测试代码和每条测试的 README。
- GitHub Actions 负责保存原始执行产物。
- Jira 负责缺陷跟踪、回归状态和任务协作。
