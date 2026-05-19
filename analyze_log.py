from __future__ import annotations

import argparse
import json
from pathlib import Path


TYPE_DATA = 2


def analyze(log_path: str | Path) -> dict[str, float | int]:
    records = []
    with open(log_path, "r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    send_count = sum(1 for r in records if r.get("event") == "send")
    recv_count = sum(1 for r in records if r.get("event") == "recv")
    timeout_count = sum(1 for r in records if r.get("event") == "timeout")
    retransmit_count = sum(1 for r in records if r.get("event") == "retransmit")
    drop_count = sum(1 for r in records if r.get("event") == "send_drop")
    corrupt_count = sum(1 for r in records if r.get("event") == "send_corrupt")
    ack_count = sum(1 for r in records if r.get("event") == "ack_sent")
    ack_received_count = sum(1 for r in records if r.get("event") == "ack_received")
    out_of_order_drop_count = sum(1 for r in records if r.get("event") == "discard_out_of_order")
    corrupted_drop_count = sum(1 for r in records if r.get("event") == "discard_corrupted")
    malformed_recv_count = sum(1 for r in records if r.get("event") == "recv_malformed")
    window_advance_count = sum(1 for r in records if r.get("event") == "window_advanced")
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze GBN JSONL logs")
    parser.add_argument("log", help="Path to JSONL log")
    args = parser.parse_args()

    result = analyze(args.log)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
