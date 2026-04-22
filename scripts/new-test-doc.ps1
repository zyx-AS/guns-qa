param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("unit", "integration", "system", "performance")]
    [string]$Type,

    [Parameter(Mandatory = $true)]
    [string]$TestId,

    [Parameter(Mandatory = $true)]
    [string]$Title,

    [string]$CodeRef = "待补充",
    [string]$Jira = "待补充",
    [string]$Workflow = "待补充"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$targetDir = Join-Path $root "guns-tests\docs\$Type\$TestId"
$targetFile = Join-Path $targetDir "README.md"

if (Test-Path $targetFile) {
    throw "Target README already exists: $targetFile"
}

switch ($Type) {
    "unit" {
        $typeName = "单元测试"
        $section3 = "- 被测类/方法：待补充`n- 被测版本：待补充`n- 测试环境：待补充`n- 测试工具：待补充`n- Mock/桩对象说明：待补充"
        $section5 = "1. 待补充。`n2. 待补充。`n3. 待补充。"
        $section7 = "- 是否通过：待补充`n- 发现问题：待补充`n- 问题编号（Jira）：待补充`n- 是否影响后续测试：待补充"
    }
    "integration" {
        $typeName = "集成测试"
        $section3 = "- 参与模块：待补充`n- 集成方式：待补充`n- 被测版本：待补充`n- 测试环境：待补充`n- 测试数据：待补充`n- 依赖服务状态：待补充"
        $section5 = "1. 模块间调用正确。`n2. 数据传递正确。`n3. 无接口异常或集成冲突。"
        $section7 = "- 是否通过：待补充`n- 发现问题：待补充`n- 问题编号（Jira）：待补充`n- 是否阻塞后续系统测试：待补充"
    }
    "system" {
        $typeName = "系统测试"
        $section3 = "- 被测模块/页面：待补充`n- 被测版本：待补充`n- 测试环境：待补充`n- 浏览器/客户端：待补充`n- 测试账号与数据：待补充`n- 依赖服务状态：待补充"
        $section5 = "1. 页面/接口响应正确。`n2. 业务流程正常完成。`n3. 数据结果符合预期。"
        $section7 = "- 是否通过：待补充`n- 发现问题：待补充`n- 问题编号（Jira）：待补充`n- 是否影响验收/上线：待补充"
    }
    "performance" {
        $typeName = "性能测试"
        $section3 = "- 被测对象：待补充`n- 被测版本：待补充`n- 测试环境：待补充`n- 测试工具：待补充`n- 测试时长：待补充`n- 并发用户数/线程数：待补充`n- 测试数据规模：待补充"
        $section5 = "- 平均响应时间：待补充`n- P95/P99：待补充`n- 吞吐量：待补充`n- 错误率：待补充`n- CPU/内存/数据库连接占用：待补充"
        $section7 = "- 是否达标：待补充`n- 性能瓶颈：待补充`n- 问题编号（Jira）：待补充`n- 是否影响系统发布：待补充"
    }
}

$template = @'
# __TITLE__（__TEST_ID__）

| 字段 | 内容 |
| --- | --- |
| 测试类型 | __TYPE_NAME__ |
| 测试编号 | `__TEST_ID__` |
| 对应代码 | `__CODE_REF__` |
| Jira | `__JIRA__` |
| GitHub 工作流 | `__WORKFLOW__` |

## 1. 测试目的
说明本测试要验证的对象、规则或场景。

## 2. 测试方法与设计依据
说明采用的测试方法、设计思路和覆盖重点。

## 3. 前置条件
__SECTION3__

## 4. 测试步骤
1. 待补充。
2. 待补充。
3. 待补充。

## 5. 预期结果
__SECTION5__

## 6. 实际结果
按老师易读的方式概括本次执行结果，并引用 GitHub Actions、Jira 或 artifact 作为证据来源。

## 7. 结论
__SECTION7__

## 8. 测试过程中的差异情况
- 差异内容：待补充
- 原因：待补充
- 对测试有效性的影响：待补充
- 是否需要重测：待补充
'@

$content = $template.Replace("__TITLE__", $Title)
$content = $content.Replace("__TEST_ID__", $TestId)
$content = $content.Replace("__TYPE_NAME__", $typeName)
$content = $content.Replace("__CODE_REF__", $CodeRef)
$content = $content.Replace("__JIRA__", $Jira)
$content = $content.Replace("__WORKFLOW__", $Workflow)
$content = $content.Replace("__SECTION3__", $section3)
$content = $content.Replace("__SECTION5__", $section5)
$content = $content.Replace("__SECTION7__", $section7)

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Set-Content -LiteralPath $targetFile -Value $content -Encoding UTF8
Write-Host "Created $targetFile"
