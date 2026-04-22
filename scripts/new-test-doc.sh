#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: bash scripts/new-test-doc.sh <unit|integration|system|performance> <TEST_ID> <TITLE> [CODE_REF] [JIRA] [WORKFLOW]" >&2
  exit 1
fi

type="$1"
test_id="$2"
title="$3"
code_ref="${4:-待补充}"
jira="${5:-待补充}"
workflow="${6:-待补充}"

case "$type" in
  unit)
    type_name="单元测试"
    section3=$'- 被测类/方法：待补充\n- 被测版本：待补充\n- 测试环境：待补充\n- 测试工具：待补充\n- Mock/桩对象说明：待补充'
    section5=$'1. 待补充。\n2. 待补充。\n3. 待补充。'
    section7=$'- 是否通过：待补充\n- 发现问题：待补充\n- 问题编号（Jira）：待补充\n- 是否影响后续测试：待补充'
    ;;
  integration)
    type_name="集成测试"
    section3=$'- 参与模块：待补充\n- 集成方式：待补充\n- 被测版本：待补充\n- 测试环境：待补充\n- 测试数据：待补充\n- 依赖服务状态：待补充'
    section5=$'1. 模块间调用正确。\n2. 数据传递正确。\n3. 无接口异常或集成冲突。'
    section7=$'- 是否通过：待补充\n- 发现问题：待补充\n- 问题编号（Jira）：待补充\n- 是否阻塞后续系统测试：待补充'
    ;;
  system)
    type_name="系统测试"
    section3=$'- 被测模块/页面：待补充\n- 被测版本：待补充\n- 测试环境：待补充\n- 浏览器/客户端：待补充\n- 测试账号与数据：待补充\n- 依赖服务状态：待补充'
    section5=$'1. 页面/接口响应正确。\n2. 业务流程正常完成。\n3. 数据结果符合预期。'
    section7=$'- 是否通过：待补充\n- 发现问题：待补充\n- 问题编号（Jira）：待补充\n- 是否影响验收/上线：待补充'
    ;;
  performance)
    type_name="性能测试"
    section3=$'- 被测对象：待补充\n- 被测版本：待补充\n- 测试环境：待补充\n- 测试工具：待补充\n- 测试时长：待补充\n- 并发用户数/线程数：待补充\n- 测试数据规模：待补充'
    section5=$'- 平均响应时间：待补充\n- P95/P99：待补充\n- 吞吐量：待补充\n- 错误率：待补充\n- CPU/内存/数据库连接占用：待补充'
    section7=$'- 是否达标：待补充\n- 性能瓶颈：待补充\n- 问题编号（Jira）：待补充\n- 是否影响系统发布：待补充'
    ;;
  *)
    echo "Unsupported type: $type" >&2
    exit 1
    ;;
esac

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_dir="$root_dir/guns-tests/docs/$type/$test_id"
target_file="$target_dir/README.md"

if [[ -f "$target_file" ]]; then
  echo "Target README already exists: $target_file" >&2
  exit 1
fi

mkdir -p "$target_dir"

cat > "$target_file" <<EOF
# ${title}（${test_id}）

| 字段 | 内容 |
| --- | --- |
| 测试类型 | ${type_name} |
| 测试编号 | \`${test_id}\` |
| 对应代码 | \`${code_ref}\` |
| Jira | \`${jira}\` |
| GitHub 工作流 | \`${workflow}\` |

## 1. 测试目的
说明本测试要验证的对象、规则或场景。

## 2. 测试方法与设计依据
说明采用的测试方法、设计思路和覆盖重点。

## 3. 前置条件
${section3}

## 4. 测试步骤
1. 待补充。
2. 待补充。
3. 待补充。

## 5. 预期结果
${section5}

## 6. 实际结果
按老师易读的方式概括本次执行结果，并引用 GitHub Actions、Jira 或 artifact 作为证据来源。

## 7. 结论
${section7}

## 8. 测试过程中的差异情况
- 差异内容：待补充
- 原因：待补充
- 对测试有效性的影响：待补充
- 是否需要重测：待补充
EOF

echo "Created $target_file"
