# 性能分析模板

本文档用于后续手工补全实验数据。仓库中已有的真实数据已单独列出；其余空白项请在重新运行实验后填写。

## 一、指标定义

建议统一采用以下指标：

- 文件大小 `file_size_bytes`
- `DataSize`
- `SWSize`
- `ErrorRate`
- `LostRate`
- `Timeout`
- 总发送次数 `send_count`
- 新发送 PDU 数量 `new_send_count`
  说明：`analyze_log.py` 当前未直接给出，需要用日志筛选 `event=send` 且 `retransmission=false`
- 超时次数 `timeout_count`
- timeout 重传次数 `retransmit_count`
- 接收正确 PDU 数量
  说明：可用 `accept_in_order` 次数
- 数据错误 PDU 数量
  说明：可用 `discard_corrupted` 次数
- 序号错误 PDU 数量
  说明：可用 `discard_out_of_order` 次数
- 总耗时 `total_time_sec`
- 吞吐率 `throughput_Bps`
- 传输效率 `efficiency`
  建议公式：`原始文件大小 / payload_bytes`

## 二、仓库中已有真实数据

| 场景 | file_size_bytes | DataSize | SWSize | ErrorRate | LostRate | Timeout | send_count | timeout_count | retransmit_count | corrupted_drop_count | out_of_order_drop_count | total_time_sec | throughput_Bps | 依据 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 单向无损 sender | 3145728 | 1024 | 8 | 0.0 | 0.0 | 0.5 | 6148 | 0 | 0 | 0 | 0 | 5.404289 | 1164159.80 | `logs/host1_send.jsonl` |
| 单向丢包 sender | 3145728 | 1024 | 8 | 0.0 | 0.03 | 0.3 | 11070 | 272 | 2176 | 0 | 0 | 48.645117 | 232901.81 | `logs/host1_loss_send.jsonl` |
| 单向差错 sender | 3145728 | 1024 | 8 | 0.02 | 0.0 | 0.3 | 3506 | 54 | 432 | 0 | 0 | 29.894853 | 120023.87 | `logs/host1_error_send.jsonl` |
| 单向丢包 receiver | 3145728 | 1024 | 8 | 0.0 | 0.03 | 0.3 | 10752 | 0 | 0 | 0 | 1848 | 60.589101 | 186989.67 | `logs/host2_loss_recv.jsonl` |
| 单向差错 receiver | 3145728 | 1024 | 8 | 0.02 | 0.0 | 0.3 | 3506 | 0 | 0 | 62 | 370 | 39.898719 | 89930.11 | `logs/host2_error_recv.jsonl` |

## 三、实验记录表

```csv
scenario,file_size_bytes,data_size,sw_size,error_rate,lost_rate,timeout_sec,send_count,new_send_count,timeout_count,retransmit_count,accept_in_order_count,discard_corrupted_count,discard_out_of_order_count,total_time_sec,throughput_Bps,efficiency,log_path
clean_3mb,,,,,,,,,,,,,,,,,
loss_3mb,,,,,,,,,,,,,,,,,
error_3mb,,,,,,,,,,,,,,,,,
window_1,,,,,,,,,,,,,,,,,
window_4,,,,,,,,,,,,,,,,,
window_8,,,,,,,,,,,,,,,,,
window_16,,,,,,,,,,,,,,,,,
timeout_0.1,,,,,,,,,,,,,,,,,
timeout_0.3,,,,,,,,,,,,,,,,,
timeout_0.5,,,,,,,,,,,,,,,,,
timeout_1.0,,,,,,,,,,,,,,,,,
datasize_512,,,,,,,,,,,,,,,,,
datasize_1024,,,,,,,,,,,,,,,,,
datasize_2048,,,,,,,,,,,,,,,,,
datasize_4096,,,,,,,,,,,,,,,,,
```

## 四、图表建议

### 1. 窗口大小 vs 吞吐率

- 横轴：`SWSize`
- 纵轴：`throughput_Bps`
- 对照条件：固定 `DataSize`, `Timeout`, `ErrorRate`, `LostRate`

### 2. 丢包率 vs 重传次数

- 横轴：`LostRate`
- 纵轴：`retransmit_count`

### 3. 错误率 vs checksum 错误数量

- 横轴：`ErrorRate`
- 纵轴：`discard_corrupted_count`

### 4. timeout vs 总耗时

- 横轴：`Timeout`
- 纵轴：`total_time_sec`

### 5. DataSize vs 吞吐率

- 横轴：`DataSize`
- 纵轴：`throughput_Bps`

## 五、分析文字模板

### 1. 无损场景分析

在无丢包、无差错条件下，发送端无需超时重传，累计 ACK 能连续推进，系统吞吐率达到本组实验中的最高值。该结果说明当前 GBN 实现能够在理想链路条件下稳定完成文件传输。

### 2. 丢包场景分析

当 `LostRate` 增大时，最早未确认 PDU 更容易长时间得不到 ACK，从而触发 timeout。由于本项目实现的是 Go-Back-N，timeout 后需要重传当前窗口内全部未确认 PDU，因此重传次数和总耗时都会增加，吞吐率下降。

### 3. 差错场景分析

当 `ErrorRate` 增大时，接收端会检测到更多 checksum 错误并丢弃损坏 PDU，发送端则因累计 ACK 无法继续前移而产生更多 timeout 与重传。该现象说明 CRC-CCITT 与错误恢复路径已被实际触发。

### 4. 窗口大小分析

窗口大小较小时，发送端并发在途 PDU 数少，链路利用率受限；窗口大小增大后，理论上可以提高吞吐率。但在丢包环境中，窗口过大也会导致一次 timeout 触发更多回退重传，因此需要通过实验寻找折中参数。

### 5. DataSize 分析

较小 `DataSize` 会增加 PDU 数量和协议头占比，带来更高控制开销；较大 `DataSize` 可减少 PDU 数量，但若出现丢包或差错，单个 PDU 的重传代价也会更高。实际最优值需要结合实验结果确定。

## 六、需要人工补充的内容

- 多组 `SWSize` 对比结果
- 多组 `Timeout` 对比结果
- 多组 `DataSize` 对比结果
- 多组 `LostRate` 对比结果
- 多组 `ErrorRate` 对比结果
- 统一口径下的“传输效率”公式与实际数值
