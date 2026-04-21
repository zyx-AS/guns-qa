# guns-qa

`guns-qa` 是 GUNS 项目的公共测试仓库。它不长期保存 GUNS 源码，而是把
“测试资产 + GitHub Actions + Jira/Xray 回填”放在一起，方便团队成员在统一
流程下执行真实的 GUNS 测试。

## 现在已经自动化到哪一步

当前主 workflow 位于 `.github/workflows/ci.yml`，名称是 `GUNS Unit Test`。

它已经能自动完成这些事：

1. 在 `push main`、`pull_request`、`workflow_dispatch` 时自动触发
2. 自动启动 GitHub-hosted runner
3. 自动安装 Java 17
4. 自动拉取开源 GUNS 源码
5. 自动切到固定的 GUNS 版本
6. 自动把本仓库里的测试资产复制进 GUNS 工作区
7. 自动执行选定的 GUNS 单元测试
8. 自动上传 surefire 报告和运行元数据
9. 自动把 JUnit XML 导入 Xray
10. 自动在 Jira 里生成对应的 `Test Execution`

当前默认测试类是：

`cn.stylefeng.guns.core.security.BlackWhiteInterceptorTest`

当前默认固定的 GUNS 提交是：

`84272f5a324e0d7890d241d7ae9afa7398da49fa`

## 它不是怎么工作的

这套仓库不是把整个 GUNS 项目复制进来。

实际流程是：

1. GitHub Actions 运行时拉取上游 GUNS
2. `guns-tests/` 中的测试资产被注入到临时工作区
3. Maven 在临时工作区执行测试
4. 生成的 JUnit XML 再导入 Xray

这样做的好处是：

- 不依赖那台性能很弱的共享服务器
- 团队成员本地不需要先统一配完整环境才能验证流程
- 测试执行和 Jira/Xray 记录可以放到统一的 GitHub CI 上

## Jira / Xray 使用说明

日常协作建议始终围绕普通 Jira Task 展开，不要拿 Xray 的 `Test Set` 或
`Test Execution` 代替开发任务。

推荐流程：

1. 先建或选择一张普通 Jira Task，例如 `GUNSQA-32`
2. 分支名带上 key，例如 `GUNSQA-32-guns-runner-workflow`
3. commit message 带上 key，例如 `GUNSQA-32 connect Xray auto import`
4. PR 标题带上 key
5. GitHub Actions 跑完后，在 Jira Development 面板看分支、commit、PR
6. 在 Xray / Jira 中看自动创建的 `Test Execution`

说明：

- Jira Development 面板显示的是 GitHub 开发活动
- Xray 里显示的是测试执行结果
- 两者是互补关系，不是二选一

## 必须配置的 GitHub Secrets

要让 Xray 自动回填生效，仓库必须配置这两个 Actions secrets：

- `XRAY_CLIENT_ID`
- `XRAY_CLIENT_SECRET`

本仓库当前 workflow 默认使用：

- `XRAY_BASE_URL=https://us.xray.cloud.getxray.app`
- `XRAY_PROJECT_KEY=GUNSQA`

如果以后换 Xray 区域或项目 key，再修改 workflow 里的环境变量即可。

## 手动触发时可以改什么

`workflow_dispatch` 支持这三个输入：

- `guns_ref`
  说明：指定要测试的 GUNS commit、tag 或 branch
- `test_class`
  说明：指定要运行的完整 JUnit 测试类名
- `jira_issue_key`
  说明：可选；手动触发时显式指定对应 Jira Task key，便于 Xray Test Execution 命名

## 本地复现

Windows：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_guns_unit_test.ps1
```

Linux 或 macOS：

```bash
bash scripts/run_guns_unit_test.sh
```

如果已经生成了 surefire XML，也可以单独导入 Xray：

```bash
XRAY_CLIENT_ID=... XRAY_CLIENT_SECRET=... bash scripts/import_xray_results.sh
```

## 仓库里几个关键目录

- `guns-tests/`
  说明：存放注入到 GUNS 工作区的测试资产
- `scripts/run_guns_unit_test.sh`
  说明：Linux/macOS/GitHub Actions 测试执行入口
- `scripts/run_guns_unit_test.ps1`
  说明：Windows 本地执行入口
- `scripts/import_xray_results.sh`
  说明：把 surefire/JUnit XML 导入 Xray 的脚本
- `.artifacts/guns/`
  说明：本地或 CI 生成的测试报告、元数据、Xray 导入结果

## 目前还没自动化的部分

现在已经有“自动执行测试 + 自动导入 Xray”，但还没有自动做这些事：

- 不会自动给普通 Jira Task 写评论
- 不会自动切换 Jira Task 状态
- 不会自动把 Test Execution 反向挂回某张普通 Task 的评论区

所以目前最稳的理解是：

- GitHub 负责执行
- Jira 负责任务协作
- Xray 负责记录测试结果

## 给接手人的一句话

如果你只想快速确认流程有没有通，直接看一次带 Jira key 的 PR 是否触发了
`GUNS Unit Test`，然后去 Jira/Xray 里确认有没有新生成的 `Test Execution`
即可。
