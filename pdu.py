from __future__ import annotations

import struct
from dataclasses import dataclass

from crc_ccitt import crc_ccitt


TYPE_START = 1
TYPE_DATA = 2
TYPE_ACK = 3
TYPE_END = 4

# type:1, seq:4, ack:4, data_len:2, checksum:2
HEADER_FORMAT = "!BIIHH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


@dataclass
class PDU:
    pdu_type: int
    seq: int
    ack: int
    data: bytes = b""

    def encode(self) -> bytes:
        data_len = len(self.data)
        header_wo_checksum = struct.pack(
            HEADER_FORMAT,
            self.pdu_type,
            self.seq,
            self.ack,
            data_len,
            0,
        )
        checksum = crc_ccitt(header_wo_checksum + self.data)
        header = struct.pack(
            HEADER_FORMAT,
            self.pdu_type,
            self.seq,
            self.ack,
            data_len,
            checksum,
        )
        return header + self.data

    @staticmethod
    def decode(packet: bytes) -> tuple["PDU", bool]:
        if len(packet) < HEADER_SIZE:
            raise ValueError("Packet too short")

        pdu_type, seq, ack, data_len, checksum = struct.unpack(
            HEADER_FORMAT, packet[:HEADER_SIZE]
        )
        data = packet[HEADER_SIZE:]
        if len(data) != data_len:
            raise ValueError("data_len mismatch")

        header_wo_checksum = struct.pack(
            HEADER_FORMAT,
            pdu_type,
            seq,
            ack,
            data_len,
            0,
        )
        expected = crc_ccitt(header_wo_checksum + data)
        return PDU(pdu_type=pdu_type, seq=seq, ack=ack, data=data), expected == checksum
