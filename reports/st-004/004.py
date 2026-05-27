import json
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体（避免中文乱码）
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False

# 1. 加载JSON数据
data_str = """
{
    "root_group": {
        "name": "",
        "path": "",
        "id": "d41d8cd98f00b204e9800998ecf8427e",
        "groups": {},
        "checks": {
                "login status is 200": {
                    "name": "login status is 200",
                    "path": "::login status is 200",
                    "id": "baba87e761865dc93085ee0c1fe25f4c",
                    "passes": 3622,
                    "fails": 0
                },
                "index status is 200": {
                    "name": "index status is 200",
                    "path": "::index status is 200",
                    "id": "013fd8182e119bea987fd95ffd7047fd",
                    "passes": 3622,
                    "fails": 0
                }
            }
    },
    "metrics": {
        "http_reqs": {
            "count": 7244,
            "rate": 30.164963549243524
        },
        "checks": {
            "passes": 7244,
            "fails": 0,
            "value": 1
        },
        "data_sent": {
            "count": 1068490,
            "rate": 4449.33212351342
        },
        "iteration_duration": {
            "med": 1004.1213,
            "max": 1028.8223,
            "p(90)": 1008.38347,
            "p(95)": 1010.499375,
            "avg": 1004.8830534787406,
            "min": 1000.3294
        },
        "http_req_blocked": {
            "p(95)": 0,
            "avg": 0.028923964660408603,
            "min": 0,
            "med": 0,
            "max": 16.4842,
            "p(90)": 0
        },
        "http_req_duration{expected_response:true}": {
            "p(95)": 3.5425399999999976,
            "avg": 1.5420548177802298,
            "min": 0,
            "med": 1.3237,
            "max": 19.7031,
            "p(90)": 2.59218
        },
        "http_req_tls_handshaking": {
            "avg": 0,
            "min": 0,
            "med": 0,
            "max": 0,
            "p(90)": 0,
            "p(95)": 0
        },
        "http_req_sending": {
            "avg": 0.03194751518498068,
            "min": 0,
            "med": 0,
            "max": 10.9859,
            "p(90)": 0,
            "p(95)": 0
        },
        "http_req_connecting": {
            "p(90)": 0,
            "p(95)": 0,
            "avg": 0.01821000828271673,
            "min": 0,
            "med": 0,
            "max": 8.0982
        },
        "http_req_receiving": {
            "min": 0,
            "med": 0,
            "max": 4.5831,
            "p(90)": 0.7221099999999999,
            "p(95)": 0.9214249999999997,
            "avg": 0.17656101601325241
        },
        "vus_max": {
            "value": 20,
            "min": 20,
            "max": 20
        },
        "http_req_failed": {
            "passes": 0,
            "fails": 7244,
            "thresholds": {
                "rate<0.01": false
            },
            "value": 0
        },
        "http_req_duration": {
            "max": 19.7031,
            "p(90)": 2.59218,
            "p(95)": 3.5425399999999976,
            "avg": 1.5420548177802298,
            "min": 0,
            "med": 1.3237,
            "thresholds": {
                "p(95)<800": false
            }
        },
        "http_req_waiting": {
            "p(95)": 3.1367399999999988,
            "avg": 1.333546286581998,
            "min": 0,
            "med": 1.0658,
            "max": 19.7031,
            "p(90)": 2.36156
        },
        "vus": {
            "value": 1,
            "min": 1,
            "max": 20
        },
        "data_received": {
            "count": 1152974,
            "rate": 4801.134550417657
        },
        "iterations": {
            "rate": 15.082481774621762,
            "count": 3622
        }
    }
}
"""
data = json.loads(data_str)
metrics = data["metrics"]

# 2. 提取核心指标
# 2.1 响应时间指标（http_req_duration，单位：ms）
req_duration = metrics["http_req_duration"]
duration_labels = ["最小值", "中位数", "平均值", "P90", "P95", "最大值"]
duration_values = [
    req_duration["min"],
    req_duration["med"],
    req_duration["avg"],
    req_duration["p(90)"],
    req_duration["p(95)"],
    req_duration["max"],
]

# 2.2 请求成功率/失败率
checks_passes = metrics["checks"]["passes"]
checks_fails = metrics["checks"]["fails"]
req_failed_pct = (metrics["http_req_failed"]["fails"] / metrics["http_reqs"]["count"]) * 100
req_success_pct = 100 - req_failed_pct

# 2.3 并发用户数（VUS）
vus_current = metrics["vus"]["value"]
vus_min = metrics["vus"]["min"]
vus_max = metrics["vus"]["max"]
vus_max_config = metrics["vus_max"]["value"]

# 2.4 数据传输量（单位：KB）
data_sent = metrics["data_sent"]["count"] / 1024
data_received = metrics["data_received"]["count"] / 1024

# 2.5 请求量
req_count = metrics["http_reqs"]["count"]
req_rate = metrics["http_reqs"]["rate"]

# 3. 绘制多子图
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle("基线性能测试核心指标可视化", fontsize=16, fontweight="bold")

# 子图1：HTTP请求响应时间分布
ax1 = axes[0, 0]
ax1.bar(duration_labels, duration_values, color=["#4CAF50", "#2196F3", "#FFC107", "#FF9800", "#F44336", "#9C27B0"])
ax1.set_title("HTTP请求响应时间（ms）", fontweight="bold")
ax1.set_ylabel("响应时间（ms）")
ax1.tick_params(axis="x", rotation=30)
# 标注数值
for i, v in enumerate(duration_values):
    ax1.text(i, v + 0.2, f"{v:.2f}", ha="center", va="bottom", fontsize=9)

# 子图2：请求成功率/失败率（饼图）
ax2 = axes[0, 1]
labels = ["成功请求", "失败请求"]
sizes = [req_success_pct, req_failed_pct]
colors = ["#4CAF50", "#F44336"]
wedges, texts, autotexts = ax2.pie(
    sizes, labels=labels, colors=colors, autopct="%1.2f%%", startangle=90
)
ax2.set_title("请求成功率/失败率", fontweight="bold")
# 美化饼图文字
for autotext in autotexts:
    autotext.set_color("white")
    autotext.set_fontweight("bold")

# 子图3：并发用户数（VUS）
ax3 = axes[0, 2]
vus_labels = ["当前VUS", "最小VUS", "最大VUS", "配置最大VUS"]
vus_values = [vus_current, vus_min, vus_max, vus_max_config]
ax3.bar(vus_labels, vus_values, color="#2196F3")
ax3.set_title("并发用户数（VUS）", fontweight="bold")
ax3.set_ylabel("用户数")
# 标注数值
for i, v in enumerate(vus_values):
    ax3.text(i, v + 0.5, f"{v}", ha="center", va="bottom", fontsize=10)

# 子图4：数据传输量（发送/接收）
ax4 = axes[1, 0]
transfer_labels = ["发送数据", "接收数据"]
transfer_values = [data_sent, data_received]
ax4.bar(transfer_labels, transfer_values, color=["#FF9800", "#9C27B0"])
ax4.set_title("数据传输总量（KB）", fontweight="bold")
ax4.set_ylabel("数据量（KB）")
# 标注数值
for i, v in enumerate(transfer_values):
    ax4.text(i, v + 500, f"{v:.2f} KB", ha="center", va="bottom", fontsize=9)

# 子图5：请求总量与请求率
ax5 = axes[1, 1]
req_metrics_labels = ["请求总量", "请求率（req/s）"]
req_metrics_values = [req_count, req_rate]
ax5.bar(req_metrics_labels, req_metrics_values, color=["#FFC107", "#4CAF50"])
ax5.set_title("HTTP请求总量与请求率", fontweight="bold")
ax5.set_ylabel("数值")
# 标注数值
for i, v in enumerate(req_metrics_values):
    ax5.text(i, v + 50, f"{v:.2f}", ha="center", va="bottom", fontsize=10)

# 子图6：迭代时长分布（补充指标）
ax6 = axes[1, 2]
iter_duration = metrics["iteration_duration"]
iter_labels = ["最小值", "中位数", "平均值", "P90", "P95", "最大值"]
iter_values = [
    iter_duration["min"],
    iter_duration["med"],
    iter_duration["avg"],
    iter_duration["p(90)"],
    iter_duration["p(95)"],
    iter_duration["max"],
]
ax6.plot(iter_labels, iter_values, marker="o", linewidth=2, color="#F44336", markersize=6)
ax6.set_title("迭代时长（ms）", fontweight="bold")
ax6.set_ylabel("时长（ms）")
ax6.tick_params(axis="x", rotation=30)
ax6.grid(True, alpha=0.3)

# 调整子图间距
plt.tight_layout(rect=[0, 0, 1, 0.96])

# 保存图片（可选）
plt.savefig("baseline_performance_metrics.png", dpi=300, bbox_inches="tight")

# 显示图表
plt.show()