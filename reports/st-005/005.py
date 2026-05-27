import json
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体（避免中文乱码）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# ---------------------- 1. 读取JSON数据 ----------------------
def load_json_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 替换为你的summary-005.json文件路径
data = load_json_data("summary-005.json")

# ---------------------- 2. 提取核心数据 ----------------------
# 检查项数据
checks_data = data['root_group']['checks']
check_names = []
check_passes = []
check_fails = []
for check in checks_data.values():
    check_names.append(check['name'])
    check_passes.append(check['passes'])
    check_fails.append(check['fails'])

# HTTP请求耗时指标（p95/avg/max/med）
http_duration = data['metrics']['http_req_duration']
duration_metrics = ['最小值', '中位数', '平均值', 'P90', 'P95', '最大值']
duration_values = [
    http_duration['min'],
    http_duration['med'],
    http_duration['avg'],
    http_duration['p(90)'],
    http_duration['p(95)'],
    http_duration['max']
]

# 核心性能指标（请求数、迭代数、成功率等）
core_metrics = {
    '总HTTP请求数': data['metrics']['http_reqs']['count'],
    '迭代次数': data['metrics']['iterations']['count'],
    '请求失败数': data['metrics']['http_req_failed']['fails'],
    '检查项通过数': data['metrics']['checks']['passes'],
    '检查项失败数': data['metrics']['checks']['fails'],
    '最大并发VUS': data['metrics']['vus_max']['value']
}

# ---------------------- 3. 绘图：检查项通过率/失败率 ----------------------
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# 子图1：检查项通过/失败数对比（柱状图）
x = np.arange(len(check_names))
width = 0.35
ax1.bar(x - width/2, check_passes, width, label='通过数', color='green')
ax1.bar(x + width/2, check_fails, width, label='失败数', color='red')
ax1.set_title('各检查项通过/失败数量', fontsize=14, fontweight='bold')
ax1.set_xlabel('检查项')
ax1.set_ylabel('数量')
ax1.set_xticks(x)
ax1.set_xticklabels(check_names, rotation=45, ha='right')
ax1.legend()
ax1.grid(axis='y', alpha=0.3)

# 子图2：HTTP请求耗时指标（柱状图）
ax2.bar(duration_metrics, duration_values, color=['blue', 'orange', 'purple', 'cyan', 'magenta', 'red'])
ax2.set_title('HTTP请求耗时指标（ms）', fontsize=14, fontweight='bold')
ax2.set_ylabel('耗时（ms）')
ax2.tick_params(axis='x', rotation=45)
ax2.grid(axis='y', alpha=0.3)

# 子图3：核心性能指标（横向柱状图）
core_names = list(core_metrics.keys())
core_values = list(core_metrics.values())
ax3.barh(core_names, core_values, color='teal')
ax3.set_title('核心性能指标汇总', fontsize=14, fontweight='bold')
ax3.set_xlabel('数值')
ax3.grid(axis='x', alpha=0.3)

# 子图4：检查项成功率占比（饼图）
total_checks = [sum(check_passes), sum(check_fails)]
total_labels = ['检查项通过总数', '检查项失败总数']
colors = ['#66bb6a', '#ef5350']
wedges, texts, autotexts = ax4.pie(
    total_checks, labels=total_labels, colors=colors, autopct='%1.1f%%',
    startangle=90, textprops={'fontsize': 10}
)
ax4.set_title('检查项整体通过率/失败率', fontsize=14, fontweight='bold')

# 调整布局
plt.tight_layout()

# 保存图片（可选，也可以直接show）
plt.savefig('summary-005-performance.png', dpi=300, bbox_inches='tight')

# 显示图表
plt.show()

# ---------------------- 4. 输出关键数据汇总（可选） ----------------------
print("=== 关键数据汇总 ===")
print(f"总迭代次数：{data['metrics']['iterations']['count']}")
print(f"HTTP请求P95耗时：{http_duration['p(95)']:.2f}ms")
print(f"请求失败率：{data['metrics']['http_req_failed']['value']:.1%}")
print(f"检查项通过率：{sum(check_passes)/(sum(check_passes)+sum(check_fails)):.1%}")