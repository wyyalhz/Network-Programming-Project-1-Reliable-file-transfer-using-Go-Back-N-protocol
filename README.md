# Reliable File Transfer using Go-Back-N (Python, UDP)

This project is a simple and readable course-project implementation of reliable file transfer over UDP using the Go-Back-N (GBN) protocol.

Current scope:

- Implemented and tested for `Host1 -> Host2` one-way file transfer.
- Implemented GBN sender sliding window and cumulative ACK.
- Supports Host1 and Host2 bidirectional full-duplex file transfer.
- Uses UDP datagrams, one PDU per datagram.
- Custom PDU fields: `type`, `seq`, `ack`, `data_len`, `data`, `checksum`.
- Checksum uses CRC-CCITT.
- Includes simulated packet loss and packet corruption.
- Includes JSONL logs and a log analysis script.

Future extensions such as simultaneous full-duplex transfer can be added on top of this structure.

## Project Structure

```text
Project1/
|- analyze_log.py
|- config.py
|- crc_ccitt.py
|- gbn_common.py
|- gbn_receiver.py
|- gbn_sender.py
|- host.py
|- logger_utils.py
|- pdu.py
|- configs/
|  |- host1.ini
|  |- host1_loss.ini
|  |- host1_error.ini
|  |- host2.ini
|  |- host2_loss.ini
|  |- host2_error.ini
|- README.md
```

## Config File Fields

Each host uses one INI config file with these fields:

- `UDPPort`: local UDP port
- `PeerIP`: peer IP
- `PeerPort`: peer UDP port
- `DataSize`: payload bytes per DATA PDU, must be `<= 4096`
- `ErrorRate`: probability of simulated corruption
- `LostRate`: probability of simulated loss
- `SWSize`: sender window size
- `InitSeqNo`: initial sequence number
- `Timeout`: sender timeout in seconds

In the default host configs for this submission:

- `host1.ini` uses UDP port `40527`
- `host2.ini` uses UDP port `40528`

## How to Run

Open two terminals in the project directory.

You can run the project in two ways:

- Python source mode: use `python host.py ...`
- Executable mode: use `dist\gbn_host.exe ...`

### 1. Start Host2 as receiver

```powershell
python host.py --config configs/host2.ini --mode recv --output-dir received --log logs/host2_recv.jsonl
```

Executable version:

```powershell
dist\gbn_host.exe --config configs/host2.ini --mode recv --output-dir received --log logs/host2_recv.jsonl
```

### 2. Start Host1 as sender

```powershell
python host.py --config configs/host1.ini --mode send --file test_3mb.bin --log logs/host1_send.jsonl
```

Executable version:

```powershell
dist\gbn_host.exe --config configs/host1.ini --mode send --file test_3mb.bin --log logs/host1_send.jsonl
```

## Full-Duplex Transfer

To run bidirectional full-duplex transfer, start both hosts in `duplex` mode. Each host sends one file and receives one file at the same time using the same UDP port.

Use different source file names on the two hosts so the received files are easy to distinguish.
For local loopback testing on one computer, it is best to start the two duplex commands within a few seconds of each other.

Host2:

```powershell
python host.py --config configs/host2.ini --mode duplex --file host2_data.bin --output-dir host2_received --log logs/host2_duplex.jsonl
```

Executable version:

```powershell
dist\gbn_host.exe --config configs/host2.ini --mode duplex --file host2_data.bin --output-dir host2_received --log logs/host2_duplex.jsonl
```

Host1:

```powershell
python host.py --config configs/host1.ini --mode duplex --file host1_data.bin --output-dir host1_received --log logs/host1_duplex.jsonl
```

Executable version:

```powershell
dist\gbn_host.exe --config configs/host1.ini --mode duplex --file host1_data.bin --output-dir host1_received --log logs/host1_duplex.jsonl
```

After both sides finish, compare:

- `host1_data.bin` with the file received under `host2_received\`
- `host2_data.bin` with the file received under `host1_received\`

Example MD5 check:

```powershell
Get-FileHash host1_data.bin -Algorithm MD5
Get-FileHash host2_received\host1_data.bin -Algorithm MD5
Get-FileHash host2_data.bin -Algorithm MD5
Get-FileHash host1_received\host2_data.bin -Algorithm MD5
```

If you want the receiver to save with a different file name:

```powershell
python host.py --config configs/host1.ini --mode send --file test_3mb.bin --target-name copied.bin --log logs/host1_send.jsonl
```

## Generate a 3MB Test File

```powershell
@'
from pathlib import Path
Path("test_3mb.bin").write_bytes(b"A" * 3 * 1024 * 1024)
'@ | python -
```

## Verify MD5

After transfer completes, compare MD5 values of the source and received files.

```powershell
Get-FileHash test_3mb.bin -Algorithm MD5
Get-FileHash received\test_3mb.bin -Algorithm MD5
```

If the two MD5 hashes are identical, the file transfer is correct.

## Analyze Logs

```powershell
python analyze_log.py logs/host1_send.jsonl
python analyze_log.py logs/host2_recv.jsonl
```

Executable version:

```powershell
dist\analyze_log.exe logs/host1_send.jsonl
dist\analyze_log.exe logs/host2_recv.jsonl
```

The script reports:

- total PDU-related events
- total send count
- total receive count
- ACK sent / ACK received count
- timeout count
- retransmission count
- simulated loss count
- simulated corruption count
- window advance count
- out-of-order discard count
- corrupted discard count
- total time
- throughput

For duplex logs, the script also outputs a `roles` object. This lets you inspect separate statistics for:

- `duplex_sender`
- `duplex_receiver`
- `channel`

## Test Timeout and Retransmission

You can use the loss-test configs to trigger Go-Back-N timeout retransmission:

```powershell
python host.py --config configs/host2_loss.ini --mode recv --output-dir received --log logs/host2_loss_recv.jsonl
python host.py --config configs/host1_loss.ini --mode send --file test_3mb.bin --log logs/host1_loss_send.jsonl
```

analyze the logs:

```
python analyze_log.py logs/host1_loss_send.jsonl
python analyze_log.py logs/host2_loss_recv.jsonl
```

These configs use a non-zero `LostRate`, so you should observe:

- `timeout_count > 0`
- `retransmit_count > 0`
- `out_of_order_drop_count > 0` on the receiver side in many runs

After the transfer, you can still verify MD5:

```powershell
Get-FileHash test_3mb.bin -Algorithm MD5
Get-FileHash received\test_3mb.bin -Algorithm MD5
```

## Test Packet Corruption

You can use the error-test configs to trigger CRC failure and Go-Back-N retransmission:

```powershell
python host.py --config configs/host2_error.ini --mode recv --output-dir received --log logs/host2_error_recv.jsonl
python host.py --config configs/host1_error.ini --mode send --file test_3mb.bin --log logs/host1_error_send.jsonl
```

Analyze the logs:

```powershell
python analyze_log.py logs/host1_error_send.jsonl
python analyze_log.py logs/host2_error_recv.jsonl
```

These configs use a non-zero `ErrorRate`, so you should observe:

- `corrupt_count > 0`
- `corrupted_drop_count > 0` on the receiver side in many runs
- `timeout_count > 0` and `retransmit_count > 0` in many runs, because corrupted DATA or ACK PDUs can break cumulative ACK progress

After the transfer, verify MD5 again:

```powershell
Get-FileHash test_3mb.bin -Algorithm MD5
Get-FileHash received\test_3mb.bin -Algorithm MD5
```

## Duplex with Loss

You can also run full-duplex transfer with packet loss simulation:

Host2:

```powershell
python host.py --config configs/host2_loss.ini --mode duplex --file host2_data.bin --output-dir host2_received_loss --log logs/host2_duplex_loss.jsonl
```

Host1:

```powershell
python host.py --config configs/host1_loss.ini --mode duplex --file host1_data.bin --output-dir host1_received_loss --log logs/host1_duplex_loss.jsonl
```

Analyze:

```powershell
python analyze_log.py logs/host1_duplex_loss.jsonl
python analyze_log.py logs/host2_duplex_loss.jsonl
```

Executable version:

```powershell
dist\analyze_log.exe logs/host1_duplex_loss.jsonl
dist\analyze_log.exe logs/host2_duplex_loss.jsonl
```

In many runs, the `roles.duplex_sender` section should show:

- `timeout_count > 0`
- `retransmit_count > 0`

The `roles.duplex_receiver` section often shows:

- `out_of_order_drop_count > 0`

## Duplex with Packet Corruption

You can run full-duplex transfer with corruption simulation too:

Host2:

```powershell
python host.py --config configs/host2_error.ini --mode duplex --file host2_data.bin --output-dir host2_received_error --log logs/host2_duplex_error.jsonl
```

Host1:

```powershell
python host.py --config configs/host1_error.ini --mode duplex --file host1_data.bin --output-dir host1_received_error --log logs/host1_duplex_error.jsonl
```

Analyze:

```powershell
python analyze_log.py logs/host1_duplex_error.jsonl
python analyze_log.py logs/host2_duplex_error.jsonl
```

Executable version:

```powershell
dist\analyze_log.exe logs/host1_duplex_error.jsonl
dist\analyze_log.exe logs/host2_duplex_error.jsonl
```

In many runs:

- `roles.duplex_sender.corrupt_count > 0`
- `roles.duplex_sender.timeout_count > 0`
- `roles.duplex_sender.retransmit_count > 0`
- `roles.duplex_receiver.corrupted_drop_count > 0`

After either duplex experiment, verify MD5 on both directions:

```powershell
Get-FileHash host1_data.bin -Algorithm MD5
Get-FileHash host2_received_loss\host1_data.bin -Algorithm MD5
Get-FileHash host2_data.bin -Algorithm MD5
Get-FileHash host1_received_loss\host2_data.bin -Algorithm MD5
```

## GBN Behavior in This Version

- Sender uses `SWSize` as the sliding window size.
- Receiver only accepts the `expected_seq` packet.
- Receiver sends cumulative ACK: the `ack` field always means "the last correctly received in-order sequence number".
- If a packet is corrupted or out of order, the receiver discards it and re-sends the latest correct ACK.
- If sender times out on the oldest unacknowledged packet, it retransmits all packets currently in the window, which matches Go-Back-N.
- In duplex mode, each host uses one shared UDP socket and concurrently runs one sender and one receiver thread.

## Notes About the Current Version

- This version focuses on correctness and readability for the basic GBN workflow.
- Receiver behavior matches standard GBN: only accepts `expected_seq`; out-of-order PDUs are discarded and the latest correct cumulative ACK is returned.
- For now, the main verified path is one-way transfer from `Host1` to `Host2`.
- The code already separates sender and receiver logic, so later extension to bidirectional full-duplex transmission is straightforward.
