from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


MAX_DATA_SIZE = 4096


@dataclass
class HostConfig:
    udp_port: int
    peer_ip: str
    peer_port: int
    data_size: int
    error_rate: float
    lost_rate: float
    sw_size: int
    init_seq_no: int
    timeout: float


def load_config(config_path: str | Path) -> HostConfig:
    parser = configparser.ConfigParser()
    read_files = parser.read(config_path, encoding="utf-8")
    if not read_files:
        raise FileNotFoundError(f"Config file not found: {config_path}")

    section = parser["DEFAULT"]
    data_size = section.getint("DataSize")
    if data_size <= 0 or data_size > MAX_DATA_SIZE:
        raise ValueError(f"DataSize must be in [1, {MAX_DATA_SIZE}]")

    return HostConfig(
        udp_port=section.getint("UDPPort"),
        peer_ip=section.get("PeerIP"),
        peer_port=section.getint("PeerPort"),
        data_size=data_size,
        error_rate=section.getfloat("ErrorRate"),
        lost_rate=section.getfloat("LostRate"),
        sw_size=section.getint("SWSize"),
        init_seq_no=section.getint("InitSeqNo"),
        timeout=section.getfloat("Timeout"),
    )
