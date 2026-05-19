from __future__ import annotations


def crc_ccitt(data: bytes, init_value: int = 0xFFFF) -> int:
    crc = init_value
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc
