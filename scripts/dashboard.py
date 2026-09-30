from __future__ import annotations

import argparse
import html
import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "dashboard.html"


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(percentile / 100 * len(ordered) + 0.5) - 1))
    return float(ordered[index])


def _read_records(path: Path, *, now: datetime) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    cutoff = now - timedelta(minutes=60)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            timestamp = datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if timestamp >= cutoff:
            records.append(record)
    return records


def calculate_panels(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    received = [record for record in records if record.get("event") == "request_received"]
    responses = [record for record in records if record.get("event") == "response_sent"]
    failures = [record for record in records if record.get("event") == "request_failed"]
    retrieval_events = [
        record
        for record in records
        if record.get("event") in {"response_sent", "request_failed"}
        and record.get("tool_success") is not None
    ]

    latencies = [float(record["latency_ms"]) for record in responses if "latency_ms" in record]
    ttft = [float(record["ttft_ms"]) for record in responses if "ttft_ms" in record]
    costs = [float(record["cost_usd"]) for record in responses if "cost_usd" in record]
    tokens_in = sum(int(record.get("tokens_in", 0)) for record in responses)
    tokens_out = sum(int(record.get("tokens_out", 0)) for record in responses)
    quality = [float(record["quality_score"]) for record in responses if "quality_score" in record]

    return {
        "latency": {
            "p50": round(_percentile(latencies, 50), 2),
            "p95": round(_percentile(latencies, 95), 2),
            "p99": round(_percentile(latencies, 99), 2),
            "ttft_p95": round(_percentile(ttft, 95), 2),
        },
        "traffic": {
            "requests": len(received),
            "rate_per_minute": round(len(received) / 60, 2),
        },
        "errors": {
            "error_rate_pct": round(100 * len(failures) / len(received), 2) if received else 0.0,
            "retrieval_success_rate_pct": round(
                100
                * sum(record.get("tool_success") is True for record in retrieval_events)
                / len(retrieval_events),
                2,
            )
            if retrieval_events
            else 0.0,
            "failures": len(failures),
        },
        "cost": {
            "total_usd": round(sum(costs), 6),
            "avg_usd": round(statistics.mean(costs), 6) if costs else 0.0,
        },
        "tokens": {"input": tokens_in, "output": tokens_out},
        "quality": {
            "mean": round(statistics.mean(quality), 4) if quality else 0.0,
        },
    }


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _panel_value(panel_id: str, metrics: dict[str, Any]) -> str:
    if panel_id == "latency":
        return (
            f"P50 {_format_value(metrics['p50'])} ms · "
            f"P95 {_format_value(metrics['p95'])} ms · "
            f"P99 {_format_value(metrics['p99'])} ms · "
            f"TTFT P95 {_format_value(metrics['ttft_p95'])} ms"
        )
    if panel_id == "traffic":
        return f"{metrics['requests']} requests · {metrics['rate_per_minute']:.2f}/min"
    if panel_id == "errors":
        return (
            f"Error {metrics['error_rate_pct']:.2f}% · "
            f"Retrieval success {metrics['retrieval_success_rate_pct']:.2f}% · "
            f"Failures {metrics['failures']}"
        )
    if panel_id == "cost":
        return f"Total ${metrics['total_usd']:.6f} · Avg ${metrics['avg_usd']:.6f}"
    if panel_id == "tokens":
        return f"Input {metrics['input']} · Output {metrics['output']}"
    return f"Mean {metrics['mean']:.4f}"


def _render_latency_timeline(
    records: list[dict[str, Any]],
    *,
    threshold_ms: float,
) -> str:
    """Render a dependency-free latency timeline for incident evidence."""
    points: list[tuple[datetime, float]] = []
    for record in records:
        if record.get("event") != "response_sent":
            continue
        try:
            timestamp = datetime.fromisoformat(str(record["ts"]).replace("Z", "+00:00"))
            latency = float(record["latency_ms"])
        except (KeyError, TypeError, ValueError):
            continue
        points.append((timestamp, latency))

    points.sort(key=lambda item: item[0])
    if not points:
        return "<div class='timeline-empty'>No response latency data in this time range.</div>"

    width, height = 760, 230
    left, right, top, bottom = 58, 18, 18, 42
    plot_width = width - left - right
    plot_height = height - top - bottom
    minimum = 0.0
    maximum = max(max(value for _, value in points), threshold_ms, 1.0)
    maximum *= 1.12
    time_start = points[0][0]
    time_end = points[-1][0]
    time_span = max((time_end - time_start).total_seconds(), 1.0)

    def x_position(timestamp: datetime) -> float:
        return left + ((timestamp - time_start).total_seconds() / time_span) * plot_width

    def y_position(value: float) -> float:
        return top + (1 - ((value - minimum) / (maximum - minimum))) * plot_height

    polyline = " ".join(
        f"{x_position(timestamp):.1f},{y_position(value):.1f}"
        for timestamp, value in points
    )
    threshold_y = y_position(threshold_ms)
    circles = "".join(
        (
            f"<circle cx='{x_position(timestamp):.1f}' cy='{y_position(value):.1f}' "
            f"r='4' class='{'incident-point' if value > threshold_ms else 'normal-point'}'>"
            f"<title>{timestamp.astimezone(timezone.utc).strftime('%H:%M:%S UTC')} — "
            f"{value:.0f} ms</title></circle>"
        )
        for timestamp, value in points
    )
    first_label = time_start.astimezone(timezone.utc).strftime("%H:%M:%S UTC")
    last_label = time_end.astimezone(timezone.utc).strftime("%H:%M:%S UTC")
    return f"""
    <div class='timeline-title'>Latency timeline · baseline → challenge window</div>
    <svg class='timeline' viewBox='0 0 {width} {height}' role='img'
         aria-label='Latency by timestamp with a {threshold_ms:.0f} millisecond threshold'>
      <line x1='{left}' y1='{top + plot_height}' x2='{width - right}' y2='{top + plot_height}' class='axis'/>
      <line x1='{left}' y1='{top}' x2='{left}' y2='{top + plot_height}' class='axis'/>
      <line x1='{left}' y1='{threshold_y:.1f}' x2='{width - right}' y2='{threshold_y:.1f}' class='threshold-line'/>
      <text x='{left - 8}' y='{top + 4}' text-anchor='end' class='axis-label'>{maximum:.0f}</text>
      <text x='{left - 8}' y='{top + plot_height + 4}' text-anchor='end' class='axis-label'>0</text>
      <text x='{width - right}' y='{threshold_y - 6:.1f}' text-anchor='end' class='threshold-label'>threshold {threshold_ms:.0f} ms</text>
      <polyline points='{polyline}' class='latency-line'/>
      {circles}
      <text x='{left}' y='{height - 12}' class='axis-label'>{html.escape(first_label)}</text>
      <text x='{width - right}' y='{height - 12}' text-anchor='end' class='axis-label'>{html.escape(last_label)}</text>
    </svg>
    <div class='timeline-legend'><span class='legend-normal'></span> within threshold
      <span class='legend-incident'></span> above threshold</div>
    """


def render_dashboard(
    records: list[dict[str, Any]],
    dashboard_config: dict[str, Any],
    *,
    generated_at: datetime,
) -> str:
    dashboard = dashboard_config["dashboard"]
    panel_metrics = calculate_panels(records)
    latency_panel = next(panel for panel in dashboard["panels"] if panel["id"] == "latency")
    latency_threshold = float(latency_panel["threshold"]["value"])
    cards: list[str] = []
    for panel in dashboard["panels"]:
        panel_id = panel["id"]
        threshold = panel["threshold"]
        threshold_text = (
            f"{threshold['aggregation']} {threshold['operator']} {threshold['value']} {panel['unit']}"
        )
        timeline = (
            _render_latency_timeline(records, threshold_ms=latency_threshold)
            if panel_id == "latency"
            else ""
        )
        cards.append(
            f"<section class='panel{' latency-panel' if panel_id == 'latency' else ''}'>"
            f"<h2>{html.escape(panel['title'])}</h2>"
            f"<div class='value'>{html.escape(_panel_value(panel_id, panel_metrics[panel_id]))}</div>"
            f"<div class='meta'>Unit: {html.escape(str(panel['unit']))}</div>"
            f"<div class='threshold'>Threshold: {html.escape(threshold_text)}</div>"
            f"{timeline}"
            "</section>"
        )

    generated = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="30">
  <title>{html.escape(dashboard['title'])}</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; padding: 2rem; background: #f4f7fb; color: #172033; }}
    header {{ display: flex; justify-content: space-between; gap: 1rem; align-items: end; margin-bottom: 1.5rem; }}
    h1 {{ margin: 0; font-size: 1.6rem; }}
    .meta {{ color: #596579; font-size: .9rem; margin-top: .55rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1rem; }}
    .panel {{ background: white; border: 1px solid #d8e0ec; border-radius: 12px; padding: 1.2rem; box-shadow: 0 2px 8px #20304a12; min-height: 125px; }}
    h2 {{ margin: 0 0 1rem; font-size: 1rem; }}
    .value {{ font-size: 1.25rem; font-weight: 700; line-height: 1.5; }}
    .threshold {{ margin-top: .7rem; padding-top: .7rem; border-top: 1px solid #edf0f5; color: #40536d; font-size: .88rem; }}
    .latency-panel {{ grid-column: 1 / -1; }}
    .timeline-title {{ margin-top: 1.1rem; color: #40536d; font-size: .9rem; font-weight: 650; }}
    .timeline {{ display: block; width: 100%; height: auto; margin-top: .25rem; background: #fbfcfe; border-radius: 8px; }}
    .axis {{ stroke: #9aa8bb; stroke-width: 1; }}
    .axis-label {{ fill: #596579; font-size: 11px; }}
    .threshold-line {{ stroke: #d97706; stroke-width: 2; stroke-dasharray: 7 5; }}
    .threshold-label {{ fill: #b45309; font-size: 11px; font-weight: 650; }}
    .latency-line {{ fill: none; stroke: #4263eb; stroke-width: 2.5; stroke-linejoin: round; stroke-linecap: round; }}
    .normal-point {{ fill: #4263eb; stroke: white; stroke-width: 1.5; }}
    .incident-point {{ fill: #dc2626; stroke: white; stroke-width: 1.5; }}
    .timeline-legend {{ color: #596579; font-size: .8rem; }}
    .timeline-legend span {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin: 0 .25rem 0 .8rem; }}
    .legend-normal {{ background: #4263eb; }}
    .legend-incident {{ background: #dc2626; }}
    .timeline-empty {{ margin-top: 1rem; color: #b45309; font-size: .9rem; }}
    footer {{ margin-top: 1.5rem; color: #596579; font-size: .85rem; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>{html.escape(dashboard['title'])}</h1>
      <div class="meta">Time range: {dashboard['time_range_minutes']} minutes · Refresh: {dashboard['refresh_seconds']} seconds</div>
    </div>
    <div class="meta">Generated: {generated}</div>
  </header>
  <main class="grid">{''.join(cards)}</main>
  <footer>Source: data/logs.jsonl · Six panels follow config/dashboard.yaml.</footer>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the Day 13 six-panel dashboard")
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    try:
        config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
        records = _read_records(args.log_path, now=now)
        document = render_dashboard(records, config, generated_at=now)
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        print(f"Dashboard generation failed: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8")
    print(f"Dashboard written to {args.output}")
    print(json.dumps(calculate_panels(records), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
