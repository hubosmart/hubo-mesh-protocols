[English](./README.md) | 简体中文

# hubo-mesh-protocols

**Hubo-Mesh** 的协议规范。Hubo-Mesh 是基于 MeshCore 的 LoRa mesh 终端：Hubo S3 终端（ESP32-S3）通过串口协议与底板上的协处理器（CH32）通信，并通过 BLE 连接 MeshLoRa C3 电台，使用标准 MeshCore 伴随协议及若干扩展。CH32 固件不开源，因此它的串口协议在这里以规范形式公开，方便第三方实现。本仓库只放规范，不放实现代码。

## 规范

以中文版为准；英文版是逐条跟随中文的译文。

| 规范 | English | 简体中文 |
|---|---|---|
| hubp 串口协议：终端与 CH32 之间的行格式、帧类型、命令与应答、事件、握手与保活 | [docs/en/hubp-serial.md](./docs/en/hubp-serial.md) | [docs/zh-CN/hubp-serial.md](./docs/zh-CN/hubp-serial.md) |
| C3 电台伴随协议扩展：自定义变量（`radio.rxgain`、`gps*` 等）、带范围的文本发送、默认射频参数与发射功率上限 | [docs/en/companion-extensions.md](./docs/en/companion-extensions.md) | [docs/zh-CN/companion-extensions.md](./docs/zh-CN/companion-extensions.md) |

## 相关仓库

- [hubo-meshlora-c3](https://github.com/hubosmart/hubo-meshlora-c3)：MeshLoRa C3 电台固件。
- [hubo-wadamesh](https://github.com/hubosmart/hubo-wadamesh)：Hubo S3 终端固件。
- [hubo-backpack-spec](https://github.com/hubosmart/hubo-backpack-spec)：30-Pin 背包接口规范。

## 工具

`python tools/check_lang_sync.py .` 检查 `docs/en` 与 `docs/zh-CN` 的文件名是否一致。

## 许可证

[CC BY 4.0](./LICENSE)。复用本材料时请署名：`Hubosmart, Hubo-Mesh protocol specifications`。

规范按现状提供，本文不构成任何质量或合规保证。
