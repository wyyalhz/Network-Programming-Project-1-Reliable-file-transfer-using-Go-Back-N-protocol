from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from console_reporter import ConsoleReporter
from config import HostConfig
from gbn_common import SharedGBNChannel
from logger_utils import EventLogger
from pdu import PDU, TYPE_ACK, TYPE_DATA, TYPE_END, TYPE_START


class GBNReceiver:
    def __init__(
        self,
        config: HostConfig,
        logger: EventLogger,
        reporter: ConsoleReporter | None = None,
    ):
        self.config = config
        self.logger = logger
        self.reporter = reporter

    @staticmethod
    def _md5_of_bytes(data: bytes) -> str:
        return hashlib.md5(data).hexdigest()

    def receive_file(
        self,
        channel: SharedGBNChannel,
        output_dir: str | Path,
        *,
        role: str = "receiver",
    ) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        expected_seq = self.config.init_seq_no
        last_acked_seq = max(0, expected_seq - 1)
        received = bytearray()
        out_path: Path | None = None
        expected_md5 = ""
        transfer_started_at = time.time()
        next_report_bytes = 256 * 1024

        while True:
            pdu, is_valid, _ = channel.recv_data(timeout=None)
            if pdu is None:
                continue

            if not is_valid:
                self.logger.log(
                    event="discard_corrupted",
                    role=role,
                    expected_seq=expected_seq,
                    last_acked_seq=last_acked_seq,
                )
                ack = PDU(TYPE_ACK, seq=0, ack=last_acked_seq, data=b"")
                channel.send_pdu(ack, role=role, note="ack_for_corrupted")
                self.logger.log(
                    event="ack_sent",
                    role=role,
                    ack_seq=last_acked_seq,
                    note="ack_for_corrupted",
                )
                continue

            if pdu.seq != expected_seq:
                self.logger.log(
                    event="discard_out_of_order",
                    role=role,
                    recv_seq=pdu.seq,
                    expected_seq=expected_seq,
                    last_acked_seq=last_acked_seq,
                )
                ack = PDU(TYPE_ACK, seq=0, ack=last_acked_seq, data=b"")
                channel.send_pdu(ack, role=role, note="ack_for_out_of_order")
                self.logger.log(
                    event="ack_sent",
                    role=role,
                    ack_seq=last_acked_seq,
                    note="ack_for_out_of_order",
                )
                continue

            self.logger.log(
                event="accept_in_order",
                role=role,
                seq=pdu.seq,
                pdu_type=pdu.pdu_type,
            )
            if pdu.pdu_type == TYPE_START:
                meta = json.loads(pdu.data.decode("utf-8"))
                out_path = output_dir / meta["filename"]
                expected_md5 = meta["md5"]
                if self.reporter is not None:
                    self.reporter.info(
                        f"[{role}] Start receiving {meta['filename']} "
                        f"({meta['filesize']} bytes)"
                    )
            elif pdu.pdu_type == TYPE_DATA:
                received.extend(pdu.data)
                if self.reporter is not None and len(received) >= next_report_bytes:
                    self.reporter.info(
                        f"[{role}] Received {len(received)} bytes"
                    )
                    next_report_bytes += 256 * 1024
            elif pdu.pdu_type == TYPE_END:
                if out_path is None:
                    raise RuntimeError("END received before START")
                out_path.write_bytes(received)
                actual_md5 = self._md5_of_bytes(received)
                self.logger.log(
                    event="file_written",
                    role=role,
                    file=str(out_path),
                    expected_md5=expected_md5,
                    actual_md5=actual_md5,
                    md5_ok=(actual_md5 == expected_md5),
                    elapsed=round(time.time() - transfer_started_at, 6),
                )
                ack = PDU(TYPE_ACK, seq=0, ack=pdu.seq, data=b"")
                channel.send_pdu(ack, role=role, note="ack_for_end")
                self.logger.log(
                    event="ack_sent",
                    role=role,
                    ack_seq=pdu.seq,
                    note="ack_for_end",
                )
                if self.reporter is not None:
                    self.reporter.info(
                        f"[{role}] Receive complete for {out_path.name}. "
                        f"md5_ok={actual_md5 == expected_md5}"
                    )
                return out_path

            last_acked_seq = pdu.seq
            expected_seq += 1
            ack = PDU(TYPE_ACK, seq=0, ack=last_acked_seq, data=b"")
            channel.send_pdu(ack, role=role, note="cumulative_ack")
            self.logger.log(
                event="ack_sent",
                role=role,
                ack_seq=last_acked_seq,
                note="cumulative_ack",
            )
