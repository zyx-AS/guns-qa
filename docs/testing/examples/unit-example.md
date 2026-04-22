# 单元测试 README 示例

以下示例展示如何把一条单元测试写成老师易读的 README。

# BlackWhiteInterceptor 请求拦截校验测试（UT-core-security-001）

| 字段 | 内容 |
| --- | --- |
| 测试类型 | 单元测试 |
| 测试编号 | `UT-core-security-001` |
| 对应代码 | `guns-tests/src/test/java/cn/stylefeng/guns/core/security/BlackWhiteInterceptorTest.java` |
| Jira | `GUNSQA-32` |
| GitHub 工作流 | `GUNS Unit Test` |
| GitHub 运行示例 | [run #4](https://github.com/zyx-AS/guns-qa/actions/runs/24713453774) |

## 1. 测试目的
验证 `BlackWhiteInterceptor` 在请求放行前，是否会先对客户端 IP 执行黑白名单校验。

## 2. 测试方法与设计依据
本测试采用单元测试方法，通过 Mockito 模拟依赖服务，验证拦截器方法的返回值和依赖调用行为。该用例属于典型的行为验证型单元测试。

## 3. 前置条件
- 被测类/方法：`BlackWhiteInterceptor.preHandle()`
- 被测版本：GUNS commit `84272f5a324e0d7890d241d7ae9afa7398da49fa`
- 测试环境：GitHub Actions，Ubuntu 24.04，Java 17
- 测试工具：JUnit 5、Mockito、Maven Surefire
- Mock/桩对象说明：模拟 `BlackWhiteValidateService` 以验证其调用行为

## 4. 测试步骤
1. 构造一个客户端 IP 为 `127.0.0.1` 的模拟请求。
2. 调用 `BlackWhiteInterceptor.preHandle()`。
3. 检查方法返回值。
4. 验证 `blackWhiteValidateService.totalValidate("127.0.0.1")` 是否被调用。

## 5. 预期结果
1. `preHandle()` 返回 `true`。
2. 黑白名单校验服务被正确调用一次。
3. 测试执行过程中无异常。

## 6. 实际结果
GitHub Actions 中该测试执行成功。Surefire 报告显示本次运行共执行 1 条测试，用时约 1 秒，通过 1 条，失败 0 条，错误 0 条，跳过 0 条。执行记录保存在 `guns-surefire-reports` artifact 中。

## 7. 结论
- 是否通过：通过
- 发现问题：无
- 问题编号（Jira）：无
- 是否影响后续测试：否

## 8. 测试过程中的差异情况
- 差异内容：本示例引用的是 GitHub Actions 的一次代表性运行结果。
- 原因：用于展示 README 推荐写法。
- 对测试有效性的影响：无。
- 是否需要重测：否。
