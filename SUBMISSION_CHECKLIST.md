# 最终提交清单与命名规范

## 一、推荐文件名

根据提供信息，推荐如下：

| 提交项 | 推荐文件名 |
|---|---|
| Word 报告 | `1120230527辜允泽班号待补充 ReliableFileTransferUsingGBN-项目报告.docx` |
| PPT 报告 | `1120230527辜允泽班号待补充 ReliableFileTransferUsingGBN-项目报告.pptx` |
| 源工程压缩包 | `1120230527辜允泽班号待补充 ReliableFileTransferUsingGBN-源工程.zip` |
| 可执行程序 | `1120230527ReliableFileTransferUsingGBN.exe` |

说明：根据课程要求，`.exe` 文件名不要包含中文，因此可执行程序文件名只保留学号和英文项目名。

## 二、每个提交文件应包含什么

### 1. Word 报告

- 项目背景
- 需求分析
- GBN 协议原理
- 系统架构
- PDU 结构设计
- 发送端与接收端实现
- 差错与丢包模拟
- 测试过程与截图
- 性能分析
- 总结与改进

### 2. PPT 报告

- 建议 8 到 12 页
- 覆盖背景、需求、协议原理、架构、实现、测试、性能、总结
- 若课程要求 audio narration，需要人工补充音频录制

### 3. 源工程压缩包

- 源码：`host.py`, `gbn_sender.py`, `gbn_receiver.py`, `gbn_common.py`, `pdu.py`, `crc_ccitt.py`, `config.py`, `logger_utils.py`, `analyze_log.py`
- 配置：`configs/*.ini`
- 说明文档：`README.md`
- 可选保留：典型日志 `logs/*.jsonl`
- 可选保留：典型测试文件
- 可选保留：PyInstaller `.spec`

### 4. 可执行程序

- 建议提交 `dist/gbn_host.exe`
- 若课程允许附带分析工具，可额外提交 `dist/analyze_log.exe`

## 三、打包前检查清单

| 检查项 | 是否建议 |
|---|---|
| 源码是否可运行 | 必查 |
| `configs/*.ini` 是否齐全 | 必查 |
| README 中命令是否可复现 | 必查 |
| 关键日志是否保留 | 建议 |
| 接收文件哈希一致性截图是否完成 | 建议 |
| 报告中的图表和数据是否与真实日志一致 | 必查 |
| `.exe` 是否能在 Windows 10 上启动 | 建议 |
| 提交文件名是否完全符合课程规范 | 必查 |
| 单个文件大小是否小于 250MB | 必查 |

## 四、如何避免超过 250MB

- 不要把整个 `build/` 目录都打进压缩包
- 可删除 `__pycache__/`
- 只保留有代表性的日志，而不是所有重复实验日志
- 只保留必要的测试文件
- 若已包含源码和配置，重复的中间产物可以删减

## 五、建议最终保留的最小提交集合

### 源工程压缩包内建议保留

- `host.py`
- `gbn_sender.py`
- `gbn_receiver.py`
- `gbn_common.py`
- `pdu.py`
- `crc_ccitt.py`
- `config.py`
- `logger_utils.py`
- `analyze_log.py`
- `console_reporter.py`
- `configs/`
- `README.md`
- 少量典型日志
- 少量典型测试文件
- `.spec` 文件

### 建议不保留

- `__pycache__/`
- `build/`
- 明显重复的中间日志
- 不必要的历史输出目录

## 六、提交前最终核对

1. Word 报告是否只写了仓库中真实存在的功能。
2. 测试结果是否明确区分“已有证据”和“需要人工补充”。
3. 所有图、表、截图是否能对上日志文件和代码路径。
4. `.exe` 文件名是否无中文。
5. 所有单个文件是否小于 `250MB`。
