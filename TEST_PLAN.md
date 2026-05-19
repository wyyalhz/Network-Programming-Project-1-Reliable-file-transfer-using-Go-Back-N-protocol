# 测试计划与测试用例

本文档区分“仓库中已有真实证据的测试”和“建议补做的测试计划”。

## 一、已有真实证据的测试

| 测试编号 | 测试目标 | 配置参数 | 输入文件大小 | 操作步骤 | 预期结果 | 实际结果 | 是否通过 | 证据文件 / 日志路径 |
|---|---|---|---:|---|---|---|---|---|
| T01 | 无丢包、无错误的 3MB 单向传输 | `host1.ini`, `host2.ini`, `DataSize=1024`, `SWSize=8`, `Timeout=0.5` | `3145728` B | Host2 先 `recv`，Host1 再 `send` | 正常完成，零重传，接收文件一致 | `timeout_count=0`, `retransmit_count=0`；`test_3mb.bin` 与 `received/test_3mb.bin` MD5 一致 | 通过 | `logs/host1_send.jsonl`, `logs/host2_recv.jsonl`, `received/test_3mb.bin` |
| T02 | 丢包场景下的单向传输 | `host1_loss.ini`, `host2_loss.ini`, `LostRate=0.03`, `Timeout=0.3` | `3145728` B | 按 README 中 loss 命令运行 | 出现 timeout / retransmit，但最终可恢复正确文件 | sender `timeout_count=272`, `retransmit_count=2176`；receiver `out_of_order_drop_count=1848` | 通过 | `logs/host1_loss_send.jsonl`, `logs/host2_loss_recv.jsonl` |
| T03 | 差错场景下的单向传输 | `host1_error.ini`, `host2_error.ini`, `ErrorRate=0.02`, `Timeout=0.3` | `3145728` B | 按 README 中 error 命令运行 | 出现 checksum 错误、超时、重传，但最终文件可恢复 | sender `corrupt_count=62`, `timeout_count=54`, `retransmit_count=432`；receiver `corrupted_drop_count=62` | 通过 | `logs/host1_error_send.jsonl`, `logs/host2_error_recv.jsonl` |
| T04 | 小文件全双工传输 | 默认 duplex 小文件实验 | `16384` B 双向 | 两端均以 `duplex` 模式发送小文件 | 两边都能接收并保存对方文件 | `host1_small.bin` 与 `host2_received_small/host1_small.bin` MD5 一致；`host2_small.bin` 与 `host1_received_small/host2_small.bin` MD5 一致 | 通过 | `logs/host1_duplex_small.jsonl`, `logs/host2_duplex_small.jsonl` |
| T05 | 较大文件全双工传输 | duplex big 实验 | `1572864` B 与 `1179648` B | 两端均以 `duplex` 模式发送较大文件 | 双向传输成功 | `host1_data.bin` 与 `host2_received_big/host1_data.bin` MD5 一致；`host2_data.bin` 与 `host1_received_big/host2_data.bin` MD5 一致 | 通过 | `logs/host1_duplex_big.jsonl`, `logs/host2_duplex_big.jsonl` |
| T06 | 丢包条件下全双工传输 | duplex loss 实验 | `1572864` B 与 `16384` B 等 | 两端均以 loss 配置 `duplex` 运行 | 双向传输可恢复 | 已发现接收结果目录与日志；至少 `host1_data.bin` 和 `host2_received_loss/host1_data.bin` MD5 一致 | 通过 | `logs/host1_duplex_loss.jsonl`, `logs/host2_duplex_loss.jsonl`, `host2_received_loss` |
| T07 | 差错条件下全双工传输 | duplex error 实验 | `16384` B 双向 | 两端均以 error 配置 `duplex` 运行 | 双向传输可恢复 | 已发现 `host2_small.bin` 与 `host1_received_error/host2_small.bin` MD5 一致；日志中出现 `corrupt_count` | 通过 | `logs/host1_duplex_error.jsonl`, `logs/host2_duplex_error.jsonl`, `host1_received_error` |

## 二、建议补做的测试计划

| 测试编号 | 测试目标 | 配置参数 | 输入文件大小 | 操作步骤 | 预期结果 | 实际结果 | 是否通过 | 证据文件 / 日志路径 |
|---|---|---|---:|---|---|---|---|---|
| P01 | 无丢包、无错误的小文件单向传输 | 默认配置 | `16KB` | Host2 `recv`，Host1 `send host1_small.bin` | 零超时、零重传、MD5 一致 | 需要运行实验后补充 | 需要人工补充 | 建议保存为 `logs/small_clean_send.jsonl` 等 |
| P02 | 不同窗口大小对比 | `SWSize=1,4,8,16` | `3MB` | 每个窗口大小重复运行 3 次 | 比较吞吐率和重传次数 | 需要运行实验后补充 | 需要人工补充 | 建议建表保存 |
| P03 | 不同 timeout 对比 | `Timeout=0.1,0.3,0.5,1.0` | `3MB` | 在相同 loss/error 条件下分别运行 | 比较 timeout 次数与吞吐率 | 需要运行实验后补充 | 需要人工补充 | 建议建表保存 |
| P04 | 不同 DataSize 对比 | `DataSize=512,1024,2048,4096` | `3MB` | 分别运行并分析日志 | 比较 PDU 数量和吞吐率 | 需要运行实验后补充 | 需要人工补充 | 建议建表保存 |
| P05 | 更高丢包率测试 | `LostRate=0.01,0.03,0.05,0.1` | `3MB` | 逐组运行 | 观察吞吐率下降与重传上升 | 需要运行实验后补充 | 需要人工补充 | 建议建表保存 |
| P06 | 更高错误率测试 | `ErrorRate=0.01,0.02,0.05` | `3MB` | 逐组运行 | 观察 checksum 失败与重传变化 | 需要运行实验后补充 | 需要人工补充 | 建议建表保存 |
| P07 | 目标文件重命名测试 | 默认配置 + `--target-name copied.bin` | `3MB` | 发送时加 `--target-name` | 接收端按指定名字保存 | 需要运行实验后补充 | 需要人工补充 | 建议保留接收目录截图 |

## 三、建议测试步骤模板

### 单向无损传输

```powershell
python host.py --config configs/host2.ini --mode recv --output-dir received --log logs/host2_recv.jsonl
python host.py --config configs/host1.ini --mode send --file test_3mb.bin --log logs/host1_send.jsonl
Get-FileHash test_3mb.bin -Algorithm MD5
Get-FileHash received\test_3mb.bin -Algorithm MD5
python analyze_log.py logs/host1_send.jsonl
python analyze_log.py logs/host2_recv.jsonl
```

### 单向丢包传输

```powershell
python host.py --config configs/host2_loss.ini --mode recv --output-dir received --log logs/host2_loss_recv.jsonl
python host.py --config configs/host1_loss.ini --mode send --file test_3mb.bin --log logs/host1_loss_send.jsonl
python analyze_log.py logs/host1_loss_send.jsonl
python analyze_log.py logs/host2_loss_recv.jsonl
```

### 单向差错传输

```powershell
python host.py --config configs/host2_error.ini --mode recv --output-dir received --log logs/host2_error_recv.jsonl
python host.py --config configs/host1_error.ini --mode send --file test_3mb.bin --log logs/host1_error_send.jsonl
python analyze_log.py logs/host1_error_send.jsonl
python analyze_log.py logs/host2_error_recv.jsonl
```

### 双向全双工传输

```powershell
python host.py --config configs/host2.ini --mode duplex --file host2_data.bin --output-dir host2_received --log logs/host2_duplex.jsonl
python host.py --config configs/host1.ini --mode duplex --file host1_data.bin --output-dir host1_received --log logs/host1_duplex.jsonl
```

## 四、测试记录注意事项

- 每次实验使用单独日志文件，避免覆盖
- 每次实验保留配置截图与命令截图
- 丢包/差错实验建议至少重复 3 次，避免随机性导致偶然结论
- 性能分析时，发送端与接收端的总时长口径要统一
