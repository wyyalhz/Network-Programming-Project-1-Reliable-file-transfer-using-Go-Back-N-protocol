from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


TYPE_DATA = 2


def load_records(log_path: str | Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with open(log_path, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def summarize_records(records: list[dict[str, object]]) -> dict[str, float | int]:
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
    max_in_flight_count = max(
        (int(r.get("in_flight_count", 0)) for r in records if r.get("event") == "timeout"),
        default=0,
    )
    total_pdu = send_count + recv_count + drop_count + corrupt_count
    transfer_record = next(
        (
            r
            for r in reversed(records)
            if r.get("event") in {"transfer_complete", "file_written"}
            and "elapsed" in r
        ),
        None,
    )
    if transfer_record is not None:
        total_time = float(transfer_record["elapsed"])
    else:
        timestamps = [r["time"] for r in records if "time" in r]
        total_time = (max(timestamps) - min(timestamps)) if len(timestamps) >= 2 else 0.0

    total_data_bytes = sum(
        r.get("data_len", 0)
        for r in records
        if r.get("event") in {"send", "recv"} and r.get("pdu_type") == TYPE_DATA
    )
    throughput = (total_data_bytes / total_time) if total_time > 0 else 0.0

    return {
        "total_log_records": len(records),
        "total_pdu_related_events": total_pdu,
        "send_count": send_count,
        "recv_count": recv_count,
        "timeout_count": timeout_count,
        "retransmit_count": retransmit_count,
        "drop_count": drop_count,
        "corrupt_count": corrupt_count,
        "ack_sent_count": ack_count,
        "ack_received_count": ack_received_count,
        "window_advance_count": window_advance_count,
        "out_of_order_drop_count": out_of_order_drop_count,
        "corrupted_drop_count": corrupted_drop_count,
        "malformed_recv_count": malformed_recv_count,
        "max_timeout_window_size": max_in_flight_count,
        "payload_bytes": total_data_bytes,
        "total_time_sec": round(total_time, 6),
        "throughput_Bps": round(throughput, 2),
    }


def analyze(log_path: str | Path) -> dict[str, object]:
    records = load_records(log_path)
    summary: dict[str, object] = summarize_records(records)

    role_names = sorted({str(r.get("role")) for r in records if r.get("role")})
    per_role: dict[str, dict[str, float | int]] = {}
    for role in role_names:
        role_records = [r for r in records if r.get("role") == role]
        per_role[role] = summarize_records(role_records)

    summary["roles"] = per_role
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze GBN JSONL logs")
    parser.add_argument("log", help="Path to JSONL log")
    args = parser.parse_args()

    result = analyze(args.log)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
