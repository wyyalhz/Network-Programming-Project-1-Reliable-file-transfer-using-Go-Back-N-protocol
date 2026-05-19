from __future__ import annotations

import argparse
import socket
import threading
import traceback
from pathlib import Path

from console_reporter import ConsoleReporter
from config import load_config
from gbn_common import SharedGBNChannel
from gbn_receiver import GBNReceiver
from gbn_sender import GBNSender
from logger_utils import EventLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Go-Back-N file transfer over UDP")
    parser.add_argument("--config", required=True, help="Path to host config INI file")
    parser.add_argument("--mode", required=True, choices=["send", "recv", "duplex"])
    parser.add_argument("--file", help="File to send")
    parser.add_argument("--output-dir", default="received", help="Directory for received file")
    parser.add_argument("--log", required=True, help="Path to JSONL log file")
    parser.add_argument("--target-name", help="Target filename on receiver side")
    return parser


def create_channel(config, logger: EventLogger) -> SharedGBNChannel:
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("", config.udp_port))
    channel = SharedGBNChannel(
        udp_socket=udp_sock,
        peer_addr=(config.peer_ip, config.peer_port),
        lost_rate=config.lost_rate,
        error_rate=config.error_rate,
        logger=logger,
    )
    channel.start()
    return channel


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    logger = EventLogger(args.log)
    reporter = ConsoleReporter(enabled=True)
    channel = create_channel(config, logger)
    sender = GBNSender(config, logger, reporter)
    receiver = GBNReceiver(config, logger, reporter)

    reporter.info(
        f"[host] Mode={args.mode}, local_port={config.udp_port}, "
        f"peer={config.peer_ip}:{config.peer_port}"
    )

    try:
        if args.mode == "send":
            if not args.file:
                raise SystemExit("--file is required in send mode")
            sender.send_file(channel, args.file, args.target_name, role="sender")
            reporter.info("[host] Send mode finished.")
            return

        if args.mode == "recv":
            out_path = receiver.receive_file(channel, Path(args.output_dir), role="receiver")
            print(f"Received file saved to: {out_path}")
            reporter.info("[host] Receive mode finished.")
            return

        if not args.file:
            raise SystemExit("--file is required in duplex mode")

        result: dict[str, Path] = {}
        errors: list[BaseException] = []

        def run_send() -> None:
            try:
                sender.send_file(channel, args.file, args.target_name, role="duplex_sender")
            except BaseException as exc:  # pragma: no cover - surfaced below
                logger.log(
                    event="thread_error",
                    role="duplex_sender",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    traceback=traceback.format_exc(),
                )
                errors.append(exc)

        def run_recv() -> None:
            try:
                result["received"] = receiver.receive_file(
                    channel,
                    Path(args.output_dir),
                    role="duplex_receiver",
                )
            except BaseException as exc:  # pragma: no cover - surfaced below
                logger.log(
                    event="thread_error",
                    role="duplex_receiver",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    traceback=traceback.format_exc(),
                )
                errors.append(exc)

        send_thread = threading.Thread(target=run_send)
        recv_thread = threading.Thread(target=run_recv)
        recv_thread.start()
        send_thread.start()
        send_thread.join()
        recv_thread.join()

        if errors:
            raise errors[0]
        print(f"Duplex send complete. Received file saved to: {result['received']}")
        reporter.info("[host] Duplex mode finished.")
    except KeyboardInterrupt:
        reporter.info("[host] Interrupted by Ctrl+C, shutting down.")
    finally:
        channel.close()


if __name__ == "__main__":
    main()
