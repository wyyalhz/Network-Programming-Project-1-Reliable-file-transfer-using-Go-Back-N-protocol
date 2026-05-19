from __future__ import annotations

import hashlib
import json
import os
import queue
import time
from collections import OrderedDict
from pathlib import Path

from console_reporter import ConsoleReporter
from config import HostConfig
from gbn_common import SharedGBNChannel
from logger_utils import EventLogger
from pdu import PDU, TYPE_ACK, TYPE_DATA, TYPE_END, TYPE_START


class GBNSender:
    def __init__(
        self,
        config: HostConfig,
        logger: EventLogger,
        reporter: ConsoleReporter | None = None,
    ):
        self.config = config
        self.logger = logger
        self.reporter = reporter

    def _read_chunks(self, file_path: str | Path) -> list[bytes]:
        chunks: list[bytes] = []
        with open(file_path, "rb") as fp:
            while True:
                chunk = fp.read(self.config.data_size)
                if not chunk:
                    break
                chunks.append(chunk)
        return chunks

    @staticmethod
    def _md5_of_file(file_path: str | Path) -> str:
        md5 = hashlib.md5()
        with open(file_path, "rb") as fp:
            for chunk in iter(lambda: fp.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def _build_pdus(self, file_path: str | Path, target_name: str | None) -> list[PDU]:
        file_path = Path(file_path)
        file_name = target_name or file_path.name
        file_size = file_path.stat().st_size
        file_md5 = self._md5_of_file(file_path)
        chunks = self._read_chunks(file_path)

        seq = self.config.init_seq_no
        start_payload = json.dumps(
            {
                "filename": file_name,
                "filesize": file_size,
                "md5": file_md5,
            }
        ).encode("utf-8")
        pdus = [PDU(TYPE_START, seq=seq, ack=0, data=start_payload)]
        seq += 1

        for chunk in chunks:
            pdus.append(PDU(TYPE_DATA, seq=seq, ack=0, data=chunk))
            seq += 1

        pdus.append(PDU(TYPE_END, seq=seq, ack=0, data=b""))
        return pdus

    def send_file(
        self,
        channel: SharedGBNChannel,
        file_path: str | Path,
        target_name: str | None = None,
        *,
        role: str = "sender",
    ) -> None:
        pdus = self._build_pdus(file_path, target_name)
        total_pdus = len(pdus)
        send_base = 0
        next_index = 0
        in_flight: OrderedDict[int, PDU] = OrderedDict()
        timer_started_at: float | None = None
        start_time = time.time()
        timeout_rounds = 0
        retransmitted_pdus = 0
        last_reported_percent = -1
        file_name = Path(file_path).name

        if self.reporter is not None:
            self.reporter.info(
                f"[{role}] Start sending {file_name} with {total_pdus} PDUs, "
                f"window={self.config.sw_size}, timeout={self.config.timeout}s"
            )

        while send_base < total_pdus:
            while next_index < total_pdus and next_index < send_base + self.config.sw_size:
                pdu = pdus[next_index]
                channel.send_pdu(pdu, role=role, is_retransmission=False)
                in_flight[next_index] = pdu
                if send_base == next_index:
                    timer_started_at = time.time()
                self.logger.log(
                    event="window_send",
                    role=role,
                    send_base_index=send_base,
                    next_index=next_index,
                    window_size=self.config.sw_size,
                    seq=pdu.seq,
                    pdu_type=pdu.pdu_type,
                )
                next_index += 1

            try:
                incoming, is_valid, _ = channel.recv_ack(timeout=0.2)
            except queue.Empty:
                if timer_started_at is None:
                    continue
                elapsed_since_timer_start = time.time() - timer_started_at
                if elapsed_since_timer_start < self.config.timeout:
                    continue

                timeout_rounds += 1
                if self.reporter is not None:
                    self.reporter.info(
                        f"[{role}] Timeout round {timeout_rounds}, "
                        f"retransmit {len(in_flight)} in-flight PDUs from seq {pdus[send_base].seq}"
                    )
                self.logger.log(
                    event="timeout",
                    role=role,
                    timeout_round=timeout_rounds,
                    base_index=send_base,
                    base_seq=pdus[send_base].seq,
                    next_index=next_index,
                    in_flight_count=len(in_flight),
                    waited_sec=round(elapsed_since_timer_start, 6),
                )
                for index, pdu in in_flight.items():
                    channel.send_pdu(
                        pdu,
                        role=role,
                        is_retransmission=True,
                        note="timeout_retransmit",
                    )
                    retransmitted_pdus += 1
                    self.logger.log(
                        event="retransmit",
                        role=role,
                        timeout_round=timeout_rounds,
                        seq=pdu.seq,
                        index=index,
                        base_seq=pdus[send_base].seq,
                    )
                timer_started_at = time.time()
                continue

            if incoming is None or not is_valid or incoming.pdu_type != TYPE_ACK:
                continue

            ack_seq = incoming.ack
            self.logger.log(
                event="ack_received",
                role=role,
                ack_seq=ack_seq,
                send_base_index=send_base,
                next_index=next_index,
            )
            if send_base < total_pdus and ack_seq < pdus[send_base].seq:
                self.logger.log(
                    event="ack_ignored",
                    role=role,
                    ack_seq=ack_seq,
                    expected_at_least=pdus[send_base].seq,
                )
                continue

            advanced = False
            old_send_base = send_base
            while send_base < total_pdus and pdus[send_base].seq <= ack_seq:
                in_flight.pop(send_base, None)
                send_base += 1
                advanced = True

            if advanced:
                self.logger.log(
                    event="window_advanced",
                    role=role,
                    old_send_base_index=old_send_base,
                    new_send_base_index=send_base,
                    ack_seq=ack_seq,
                    in_flight_count=len(in_flight),
                )
                percent = (send_base * 100) // total_pdus
                if self.reporter is not None and percent >= last_reported_percent + 10:
                    last_reported_percent = percent
                    self.reporter.info(
                        f"[{role}] ACK advanced to seq {ack_seq}, progress {percent}% "
                        f"({send_base}/{total_pdus} PDUs acknowledged)"
                    )
                timer_started_at = time.time() if send_base < next_index else None

        self.logger.log(
            event="transfer_complete",
            role=role,
            file=os.fspath(file_path),
            total_pdus=total_pdus,
            timeout_rounds=timeout_rounds,
            retransmitted_pdus=retransmitted_pdus,
            elapsed=round(time.time() - start_time, 6),
        )
        if self.reporter is not None:
            self.reporter.info(
                f"[{role}] Send complete for {file_name}. "
                f"timeout_rounds={timeout_rounds}, retransmitted_pdus={retransmitted_pdus}"
            )
