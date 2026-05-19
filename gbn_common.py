from __future__ import annotations

import queue
import random
import socket
import threading
from typing import Optional

from logger_utils import EventLogger
from pdu import PDU, TYPE_ACK


class SharedGBNChannel:
    def __init__(
        self,
        udp_socket: socket.socket,
        peer_addr: tuple[str, int],
        lost_rate: float,
        error_rate: float,
        logger: EventLogger,
    ) -> None:
        self.sock = udp_socket
        self.peer_addr = peer_addr
        self.lost_rate = lost_rate
        self.error_rate = error_rate
        self.logger = logger
        self._ack_queue: queue.Queue[tuple[Optional[PDU], bool, tuple[str, int]]] = queue.Queue()
        self._data_queue: queue.Queue[tuple[Optional[PDU], bool, tuple[str, int]]] = queue.Queue()
        self._send_lock = threading.Lock()
        self._running = threading.Event()
        self._recv_thread: threading.Thread | None = None

    def start(self) -> None:
        self.sock.settimeout(0.2)
        self._running.set()
        self.logger.log(event="channel_started", role="channel")
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._recv_thread is not None:
            self._recv_thread.join(timeout=1.0)

    def close(self) -> None:
        self.stop()
        self.sock.close()

    def send_pdu(
        self,
        pdu: PDU,
        *,
        role: str,
        is_retransmission: bool = False,
        note: str = "",
    ) -> bool:
        packet = pdu.encode()

        if random.random() < self.lost_rate:
            self.logger.log(
                event="send_drop",
                role=role,
                pdu_type=pdu.pdu_type,
                seq=pdu.seq,
                ack=pdu.ack,
                data_len=len(pdu.data),
                retransmission=is_retransmission,
                note=note or "simulated_loss",
            )
            return False

        if packet and random.random() < self.error_rate:
            corrupted = bytearray(packet)
            corrupted[-1] ^= 0xFF
            packet = bytes(corrupted)
            self.logger.log(
                event="send_corrupt",
                role=role,
                pdu_type=pdu.pdu_type,
                seq=pdu.seq,
                ack=pdu.ack,
                data_len=len(pdu.data),
                retransmission=is_retransmission,
                note=note or "simulated_error",
            )

        with self._send_lock:
            self.sock.sendto(packet, self.peer_addr)
        self.logger.log(
            event="send",
            role=role,
            pdu_type=pdu.pdu_type,
            seq=pdu.seq,
            ack=pdu.ack,
            data_len=len(pdu.data),
            retransmission=is_retransmission,
            note=note,
        )
        return True

    def recv_ack(self, timeout: float | None = None) -> tuple[Optional[PDU], bool, tuple[str, int]]:
        return self._ack_queue.get(timeout=timeout)

    def recv_data(self, timeout: float | None = None) -> tuple[Optional[PDU], bool, tuple[str, int]]:
        return self._data_queue.get(timeout=timeout)

    def _recv_loop(self) -> None:
        self.logger.log(event="channel_thread_started", role="channel")
        while self._running.is_set():
            try:
                try:
                    packet, addr = self.sock.recvfrom(8192)
                except socket.timeout:
                    continue
                except OSError:
                    break

                try:
                    pdu, is_valid = PDU.decode(packet)
                    self.logger.log(
                        event="recv",
                        role="channel",
                        pdu_type=pdu.pdu_type,
                        seq=pdu.seq,
                        ack=pdu.ack,
                        data_len=len(pdu.data),
                        checksum_ok=is_valid,
                    )
                except Exception as exc:
                    self.logger.log(
                        event="recv_malformed",
                        role="channel",
                        packet_len=len(packet),
                        checksum_ok=False,
                        note=str(exc),
                    )
                    self._data_queue.put((None, False, addr))
                    continue

                if addr != self.peer_addr:
                    self.logger.log(
                        event="recv_ignored_peer",
                        role="channel",
                        pdu_type=pdu.pdu_type,
                        seq=pdu.seq,
                        ack=pdu.ack,
                        note=f"unexpected_peer={addr[0]}:{addr[1]}",
                    )
                    continue

                if pdu.pdu_type == TYPE_ACK:
                    self._ack_queue.put((pdu, is_valid, addr))
                else:
                    self._data_queue.put((pdu, is_valid, addr))
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.log(
                    event="channel_thread_error",
                    role="channel",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                break
