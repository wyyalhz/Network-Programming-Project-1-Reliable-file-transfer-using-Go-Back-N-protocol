# 项目代码清单

## 源码文件

| 文件 | 作用 | 关键函数 / 类 |
|---|---|---|
| [host.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/host.py) | 程序入口；解析命令行；创建 channel；调度 send/recv/duplex | `build_parser`, `create_channel`, `main` |
| [config.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/config.py) | 读取 INI 配置并检查 `DataSize<=4096` | `HostConfig`, `load_config` |
| [pdu.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/pdu.py) | 定义 PDU 结构、类型、编解码与 checksum 校验 | `PDU`, `PDU.encode`, `PDU.decode` |
| [crc_ccitt.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/crc_ccitt.py) | CRC-CCITT 校验 | `crc_ccitt` |
| [gbn_common.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/gbn_common.py) | 共享 UDP 通道；后台收包线程；丢包/差错模拟；ACK/DATA 队列分发 | `SharedGBNChannel`, `start`, `send_pdu`, `recv_ack`, `recv_data`, `_recv_loop` |
| [gbn_sender.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/gbn_sender.py) | GBN 发送端；分块、建包、滑动窗口、ACK 处理、timeout 重传 | `GBNSender`, `_read_chunks`, `_md5_of_file`, `_build_pdus`, `send_file` |
| [gbn_receiver.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/gbn_receiver.py) | GBN 接收端；按序接收、累计 ACK、写文件、MD5 比对 | `GBNReceiver`, `_md5_of_bytes`, `receive_file` |
| [logger_utils.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/logger_utils.py) | JSONL 日志写入 | `EventLogger`, `log` |
| [analyze_log.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/analyze_log.py) | 统计日志，输出总量和分角色指标 | `load_records`, `summarize_records`, `analyze`, `main` |
| [console_reporter.py](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/console_reporter.py) | 控制台信息输出 | `ConsoleReporter`, `info` |

## 配置与构建文件

| 文件 | 作用 |
|---|---|
| [README.md](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/README.md) | 使用说明、测试命令、日志分析示例 |
| [configs/host1.ini](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/configs/host1.ini) | Host1 默认配置 |
| [configs/host2.ini](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/configs/host2.ini) | Host2 默认配置 |
| [configs/host1_loss.ini](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/configs/host1_loss.ini) | 丢包实验 Host1 配置 |
| [configs/host2_loss.ini](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/configs/host2_loss.ini) | 丢包实验 Host2 配置 |
| [configs/host1_error.ini](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/configs/host1_error.ini) | 差错实验 Host1 配置 |
| [configs/host2_error.ini](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/configs/host2_error.ini) | 差错实验 Host2 配置 |
| [gbn_host.spec](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/gbn_host.spec) | `host.py` 的 PyInstaller 打包规格 |
| [analyze_log.spec](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/analyze_log.spec) | `analyze_log.py` 的打包规格 |
| [analyze_log_exe.spec](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/analyze_log_exe.spec) | `analyze_log.py` 的另一份打包规格 |

## 日志与实验产物

| 路径 | 作用 |
|---|---|
| [logs/](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/logs) | 存放单向、丢包、差错、duplex 实验日志 |
| [received/](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/received) | 单向接收文件目录 |
| [host1_received_small/](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/host1_received_small) | Host1 收到 Host2 小文件的目录 |
| [host2_received_small/](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/host2_received_small) | Host2 收到 Host1 小文件的目录 |
| [host1_received_big/](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/host1_received_big) | Host1 收到 Host2 较大文件的目录 |
| [host2_received_big/](/E:/BIT/a3Junior/Summer/ComputerNetwork/Project1/host2_received_big) | Host2 收到 Host1 较大文件的目录 |

## 关键实现索引

### 入口与模式控制

- `host.py:17` `build_parser`：定义 `--config --mode --file --output-dir --log --target-name`
- `host.py:28` `create_channel`：创建 UDP socket，绑定本地端口，启动 `SharedGBNChannel`
- `host.py:42` `main`：根据 `send / recv / duplex` 进入不同工作模式

### PDU 与 CRC

- `pdu.py:9-12`：定义 `TYPE_START/TYPE_DATA/TYPE_ACK/TYPE_END`
- `pdu.py:15`：定义头部格式 `!BIIHH`
- `pdu.py:26`：PDU 编码
- `pdu.py:47`：PDU 解码与 checksum 校验
- `crc_ccitt.py:4`：CRC-CCITT 计算

### 发送端

- `gbn_sender.py:29` `_read_chunks`：按 `DataSize` 读取文件
- `gbn_sender.py:40` `_md5_of_file`：发送前计算源文件 MD5
- `gbn_sender.py:47` `_build_pdus`：构造 START / DATA / END PDU 序列
- `gbn_sender.py:72` `send_file`：GBN 窗口发送、ACK 处理、超时重传

### 接收端

- `gbn_receiver.py:27` `_md5_of_bytes`：接收完成后计算 MD5
- `gbn_receiver.py:30` `receive_file`：按序接收、累计 ACK、写文件、验证完整性

### 信道与异常模拟

- `gbn_common.py:36` `start`：启动后台接收线程，Windows 下关闭 UDP ConnReset
- `gbn_common.py:62` `send_pdu`：发送前执行丢包/差错模拟
- `gbn_common.py:114` `recv_ack`：取 ACK 队列
- `gbn_common.py:117` `recv_data`：取 DATA 队列
- `gbn_common.py:120` `_recv_loop`：`recvfrom` 后解码并按 ACK/DATA 分流

### 日志

- `logger_utils.py:9` `EventLogger`：线程安全日志类
- `logger_utils.py:15` `log`：按行追加 JSON

### 日志分析

- `analyze_log.py:12` `load_records`：读取 JSONL
- `analyze_log.py:22` `summarize_records`：统计事件数量和吞吐率
- `analyze_log.py:85` `analyze`：按角色细分统计

## 仓库中已可确认的功能边界

- 已确认：单向传输、全双工、GBN 滑动窗口、累计 ACK、timeout 重传、CRC-CCITT、随机丢包、随机差错、INI 配置、JSONL 日志、日志分析、Windows exe 产物
- 未确认或未实现：序号回绕、序号空间与窗口大小约束检查、多 peer 管理、自动批量实验脚本、专门图表生成脚本
