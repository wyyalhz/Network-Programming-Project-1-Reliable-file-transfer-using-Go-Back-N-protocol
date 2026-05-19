from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


TYPE_DATA = 2
DEFAULT_BATCH_FIELDS = ["sw_size", "timeout_sec", "data_size"]


def load_records(log_path: str | Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with open(log_path, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def summarize_records(records: list[dict[str, object]]) -> dict[str, float | int | str]:
    event_counts = Counter(r.get("event") for r in records)
    send_count = event_counts["send"]
    recv_count = event_counts["recv"]
    timeout_count = event_counts["timeout"]
    retransmit_count = event_counts["retransmit"]
    drop_count = event_counts["send_drop"]
    corrupt_count = event_counts["send_corrupt"]
    ack_count = event_counts["ack_sent"]
    ack_received_count = event_counts["ack_received"]
    out_of_order_drop_count = event_counts["discard_out_of_order"]
    corrupted_drop_count = event_counts["discard_corrupted"]
    malformed_recv_count = event_counts["recv_malformed"]
    window_advance_count = event_counts["window_advanced"]
    accept_in_order_count = event_counts["accept_in_order"]
    new_send_count = sum(
        1
        for r in records
        if r.get("event") == "send" and not bool(r.get("retransmission", False))
    )
    max_in_flight_count = max(
        (int(r.get("in_flight_count", 0)) for r in records if r.get("event") == "timeout"),
        default=0,
    )
    total_pdu = send_count + recv_count + drop_count + corrupt_count

    transfer_record = next(
        (
            r
            for r in reversed(records)
            if r.get("event") in {"transfer_complete", "file_written"} and "elapsed" in r
        ),
        None,
    )
    if transfer_record is not None:
        total_time = float(transfer_record["elapsed"])
    else:
        timestamps = [float(r["time"]) for r in records if "time" in r]
        total_time = (max(timestamps) - min(timestamps)) if len(timestamps) >= 2 else 0.0

    total_data_bytes = sum(
        int(r.get("data_len", 0))
        for r in records
        if r.get("event") in {"send", "recv"} and r.get("pdu_type") == TYPE_DATA
    )
    throughput = (total_data_bytes / total_time) if total_time > 0 else 0.0

    transfer_file = ""
    md5_ok = ""

    start_record = next(
        (
            r
            for r in records
            if r.get("event") == "send"
            and r.get("pdu_type") == 1
            and int(r.get("data_len", 0)) > 0
        ),
        None,
    )
    if start_record is not None and "data_len" in start_record:
        # START metadata is not stored in the log payload, so exact file size must
        # come from experiment metadata or later file_written records when present.
        transfer_file = str(start_record.get("file", ""))

    file_written_record = next(
        (r for r in reversed(records) if r.get("event") == "file_written"),
        None,
    )
    if file_written_record is not None:
        transfer_file = str(file_written_record.get("file", transfer_file))
        md5_ok = str(file_written_record.get("md5_ok", ""))

    return {
        "total_log_records": len(records),
        "total_pdu_related_events": total_pdu,
        "send_count": send_count,
        "new_send_count": new_send_count,
        "recv_count": recv_count,
        "timeout_count": timeout_count,
        "retransmit_count": retransmit_count,
        "drop_count": drop_count,
        "corrupt_count": corrupt_count,
        "ack_sent_count": ack_count,
        "ack_received_count": ack_received_count,
        "window_advance_count": window_advance_count,
        "accept_in_order_count": accept_in_order_count,
        "out_of_order_drop_count": out_of_order_drop_count,
        "corrupted_drop_count": corrupted_drop_count,
        "malformed_recv_count": malformed_recv_count,
        "max_timeout_window_size": max_in_flight_count,
        "payload_bytes": total_data_bytes,
        "transfer_file": transfer_file,
        "md5_ok": md5_ok,
        "total_time_sec": round(total_time, 6),
        "throughput_Bps": round(throughput, 2),
    }


def analyze(log_path: str | Path) -> dict[str, object]:
    records = load_records(log_path)
    summary: dict[str, object] = summarize_records(records)

    role_names = sorted({str(r.get("role")) for r in records if r.get("role")})
    per_role: dict[str, dict[str, float | int | str]] = {}
    for role in role_names:
        role_records = [r for r in records if r.get("role") == role]
        per_role[role] = summarize_records(role_records)

    summary["roles"] = per_role
    return summary


def coerce_value(value: str) -> Any:
    text = value.strip()
    if text == "":
        return ""
    lower = text.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    try:
        if any(ch in text for ch in [".", "e", "E"]):
            return float(text)
        return int(text)
    except ValueError:
        return text


def load_experiment_matrix(matrix_path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(matrix_path, "r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for raw_row in reader:
            row = {key: coerce_value(value or "") for key, value in raw_row.items() if key}
            rows.append(row)
    return rows


def select_summary_for_role(analysis: dict[str, object], role: str | None) -> dict[str, Any]:
    if not role:
        return dict(analysis)
    roles = analysis.get("roles", {})
    if isinstance(roles, dict) and role in roles:
        role_summary = dict(roles[role])
        role_summary["selected_role"] = role
        return role_summary
    raise KeyError(f"Role '{role}' not found in log summary")


def summarize_experiment_row(row: dict[str, Any], default_role: str | None) -> dict[str, Any]:
    log_path = row.get("log_path") or row.get("log")
    if not log_path:
        raise ValueError("Each experiment row must include log_path")

    analysis = analyze(log_path)
    row_role = row.get("role")
    selected_role = str(row_role) if row_role not in {"", None} else default_role
    summary = select_summary_for_role(analysis, selected_role)
    result = dict(row)
    result["log_path"] = str(log_path)
    result["selected_role"] = selected_role or "overall"
    result.update(summary)

    file_size = result.get("file_size_bytes", "")
    payload_bytes = result.get("payload_bytes", 0)
    if isinstance(file_size, (int, float)) and file_size and isinstance(payload_bytes, (int, float)) and payload_bytes:
        result["efficiency"] = round(float(file_size) / float(payload_bytes), 6)
    else:
        result["efficiency"] = ""
    return result


def write_csv(rows: list[dict[str, Any]], out_path: str | Path) -> None:
    ordered_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                ordered_keys.append(key)

    with open(out_path, "w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=ordered_keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def try_import_matplotlib():
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError:
        return None
    return plt


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def plot_metric(rows: list[dict[str, Any]], x_field: str, y_field: str, output_path: Path, title: str) -> bool:
    plt = try_import_matplotlib()
    if plt is None:
        return False

    points = [
        (float(row[x_field]), float(row[y_field]), str(row.get("label", row.get("log_path", ""))))
        for row in rows
        if is_number(row.get(x_field)) and is_number(row.get(y_field))
    ]
    if len(points) < 2:
        return False

    points.sort(key=lambda item: item[0])
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    labels = [point[2] for point in points]

    plt.figure(figsize=(8, 5))
    plt.plot(xs, ys, marker="o")
    for x, y, label in zip(xs, ys, labels):
        plt.annotate(label, (x, y), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)
    plt.title(title)
    plt.xlabel(x_field)
    plt.ylabel(y_field)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()
    return True


def build_default_plots(rows: list[dict[str, Any]], output_dir: str | Path) -> list[str]:
    created: list[str] = []
    output_dir = Path(output_dir)
    plot_targets = [
        ("throughput_Bps", "Throughput"),
        ("retransmit_count", "Retransmission Count"),
        ("timeout_count", "Timeout Count"),
    ]

    for x_field in DEFAULT_BATCH_FIELDS:
        unique_values = {
            row.get(x_field)
            for row in rows
            if is_number(row.get(x_field))
        }
        if len(unique_values) < 2:
            continue
        for y_field, title_prefix in plot_targets:
            output_path = output_dir / f"{y_field}_vs_{x_field}.png"
            title = f"{title_prefix} vs {x_field}"
            if plot_metric(rows, x_field, y_field, output_path, title):
                created.append(str(output_path))
    return created


def run_batch_analysis(matrix_path: str | Path, output_dir: str | Path, default_role: str | None) -> dict[str, Any]:
    rows = load_experiment_matrix(matrix_path)
    summaries = [summarize_experiment_row(row, default_role) for row in rows]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "batch_summary.csv"
    json_path = output_dir / "batch_summary.json"
    write_csv(summaries, csv_path)
    json_path.write_text(json.dumps(summaries, indent=2, ensure_ascii=True), encoding="utf-8")

    created_plots = build_default_plots(summaries, output_dir)
    return {
        "matrix_path": str(matrix_path),
        "output_dir": str(output_dir),
        "summary_csv": str(csv_path),
        "summary_json": str(json_path),
        "plot_files": created_plots,
        "plotting_enabled": bool(try_import_matplotlib()),
        "experiment_count": len(summaries),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze GBN JSONL logs")
    parser.add_argument("log", nargs="?", help="Path to one JSONL log")
    parser.add_argument("--batch", help="CSV file describing multiple experiments")
    parser.add_argument(
        "--output-dir",
        default="analysis_output",
        help="Directory used for batch CSV/JSON/plot outputs",
    )
    parser.add_argument(
        "--role",
        help="Role to analyze for each log, e.g. sender, receiver, duplex_sender, duplex_receiver",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.batch:
        result = run_batch_analysis(args.batch, args.output_dir, args.role)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        if not result["plotting_enabled"]:
            print(
                "Plot files were not generated because matplotlib is not installed. "
                "CSV and JSON summaries were still created."
            )
        return

    if not args.log:
        parser.error("Either a log path or --batch must be provided")

    result = analyze(args.log)
    if args.role:
        result = select_summary_for_role(result, args.role)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
