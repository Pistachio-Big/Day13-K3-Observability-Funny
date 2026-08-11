"""Dựng dashboard runtime 6 panel từ data/logs.jsonl và xuất ra PNG.

Nguồn dữ liệu chuẩn: data/logs.jsonl. Ngưỡng/đơn vị đọc từ config/dashboard.yaml
để luôn khớp contract. Ảnh xuất ra submission/evidence/cp2_dashboard.png.

Cài phụ thuộc (chỉ 1 lần):
    pip install matplotlib

Chạy:
    python scripts/build_dashboard.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DASH_PATH = REPO_ROOT / "config" / "dashboard.yaml"
OUT_PATH = REPO_ROOT / "submission" / "evidence" / "cp2_dashboard.png"


def load_records() -> list[dict]:
    if not LOG_PATH.exists():
        sys.exit(f"Không thấy {LOG_PATH}. Chạy API + load_test trước.")
    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def minute_key(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M")
    except Exception:
        return "?"


def thresholds(dash: dict) -> dict:
    out = {}
    for panel in dash["dashboard"]["panels"]:
        out[panel["id"]] = {
            "unit": panel.get("unit"),
            "op": panel["threshold"]["operator"],
            "value": panel["threshold"]["value"],
        }
    return out


def main() -> None:
    configure_utf8_stdio()
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        sys.exit("Thiếu matplotlib. Chạy: pip install matplotlib")

    records = load_records()
    dash = yaml.safe_load(DASH_PATH.read_text(encoding="utf-8"))
    th = thresholds(dash)

    resp = [r for r in records if r.get("event") == "response_sent"]
    recv = [r for r in records if r.get("event") == "request_received"]
    fail = [r for r in records if r.get("event") == "request_failed"]

    latencies = [r["latency_ms"] for r in resp if r.get("latency_ms") is not None]
    p50, p95, p99 = (percentile(latencies, p) for p in (50, 95, 99))

    traffic_by_min: dict[str, int] = defaultdict(int)
    for r in recv:
        traffic_by_min[minute_key(r.get("ts", ""))] += 1

    received_n = len(recv) or len(resp) + len(fail)
    error_n = len(fail)
    error_rate = round(error_n / received_n * 100, 2) if received_n else 0.0
    error_breakdown = Counter(r.get("error_type", "unknown") for r in fail)

    cost_by_min: dict[str, float] = defaultdict(float)
    for r in resp:
        cost_by_min[minute_key(r.get("ts", ""))] += r.get("cost_usd", 0.0) or 0.0
    total_cost = round(sum(cost_by_min.values()), 4)

    tokens_in = sum(r.get("tokens_in", 0) or 0 for r in resp)
    tokens_out = sum(r.get("tokens_out", 0) or 0 for r in resp)

    quals = [r["quality_score"] for r in resp if r.get("quality_score") is not None]
    quality_avg = round(sum(quals) / len(quals), 3) if quals else 0.0

    # ---- vẽ ----
    plt.rcParams.update({"figure.autolayout": True, "font.size": 9})
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    dash_meta = dash["dashboard"]
    fig.suptitle(
        f"{dash_meta['title']}  |  time range {dash_meta['time_range_minutes']}m  "
        f"·  refresh {dash_meta['refresh_seconds']}s  ·  source: data/logs.jsonl  "
        f"·  {datetime.now():%Y-%m-%d %H:%M}",
        fontsize=12,
        fontweight="bold",
    )
    RED = "#d62728"

    def hline(ax, value, label):
        ax.axhline(value, color=RED, linestyle="--", linewidth=1.3)
        ax.text(0.98, value, f" {label} ", color=RED, ha="right", va="bottom",
                transform=ax.get_yaxis_transform(), fontsize=8)

    # 1. Latency
    ax = axes[0][0]
    ax.bar(["p50", "p95", "p99"], [p50, p95, p99], color="#1f77b4")
    hline(ax, th["latency"]["value"], f"SLO p95 ≤ {th['latency']['value']}")
    ax.set_title("1. Latency percentiles (ms)")
    ax.set_ylabel("ms")
    for i, v in enumerate([p50, p95, p99]):
        ax.text(i, v, f"{v:.0f}", ha="center", va="bottom")

    # 2. Traffic
    ax = axes[0][1]
    mins = sorted(traffic_by_min)
    ax.bar(mins, [traffic_by_min[m] for m in mins], color="#2ca02c")
    hline(ax, th["traffic"]["value"], f"≥ {th['traffic']['value']}/min")
    ax.set_title("2. Request traffic (req/phút)")
    ax.set_ylabel("requests")
    ax.tick_params(axis="x", rotation=45)

    # 3. Errors
    ax = axes[0][2]
    if error_breakdown:
        ax.bar(list(error_breakdown), list(error_breakdown.values()), color="#ff7f0e")
    else:
        ax.text(0.5, 0.5, "0 lỗi", ha="center", va="center", transform=ax.transAxes)
    ax.set_title(f"3. Errors — rate {error_rate}%  (SLO ≤ {th['errors']['value']}%)")
    ax.set_ylabel("count")
    color = "#2ca02c" if error_rate <= th["errors"]["value"] else RED
    ax.text(0.5, 0.92, f"error_rate_pct = {error_rate}%", ha="center", va="top",
            transform=ax.transAxes, color=color, fontweight="bold")

    # 4. Cost
    ax = axes[1][0]
    mins = sorted(cost_by_min)
    ax.bar(mins, [cost_by_min[m] for m in mins], color="#9467bd")
    ax.set_title(f"4. Cost over time — total ${total_cost} (SLO ≤ ${th['cost']['value']})")
    ax.set_ylabel("usd/phút")
    ax.tick_params(axis="x", rotation=45)

    # 5. Tokens
    ax = axes[1][1]
    ax.bar(["tokens_in", "tokens_out"], [tokens_in, tokens_out], color="#8c564b")
    hline(ax, th["tokens"]["value"], f"≤ {th['tokens']['value']:,}")
    ax.set_title("5. Input/Output tokens")
    ax.set_ylabel("tokens")
    for i, v in enumerate([tokens_in, tokens_out]):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom")

    # 6. Quality
    ax = axes[1][2]
    bar_color = "#2ca02c" if quality_avg >= th["quality"]["value"] else RED
    ax.bar(["quality"], [quality_avg], color=bar_color, width=0.5)
    hline(ax, th["quality"]["value"], f"SLO ≥ {th['quality']['value']}")
    ax.set_ylim(0, 1)
    ax.set_title("6. Quality proxy (mean)")
    ax.set_ylabel("score 0–1")
    ax.text(0, quality_avg, f"{quality_avg}", ha="center", va="bottom")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=120, bbox_inches="tight")
    print(f"Đã lưu dashboard: {OUT_PATH}")
    print(
        f"KPI: p95={p95:.0f}ms · traffic={sum(traffic_by_min.values())} · "
        f"error_rate={error_rate}% · cost=${total_cost} · "
        f"tokens={tokens_in}/{tokens_out} · quality={quality_avg}"
    )


if __name__ == "__main__":
    main()
