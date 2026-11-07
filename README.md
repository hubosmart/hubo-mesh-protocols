English | [简体中文](./README.zh-CN.md)

# hubo-mesh-protocols

Protocol specifications for **Hubo-Mesh**, a LoRa mesh terminal built on MeshCore. The Hubo S3 terminal (ESP32-S3) talks to a coprocessor on its baseboard (CH32) over a serial protocol, and to the MeshLoRa C3 radio over BLE using the standard MeshCore companion protocol plus a few extensions. The CH32 firmware is not open source, so its serial protocol is published here as a specification that third parties can implement. This repository holds specifications only, no implementation code.

## Specifications

The Chinese version is authoritative; the English version is a translation that follows it clause by clause.

| Specification | English | 简体中文 |
|---|---|---|
| hubp serial protocol: line format, frame types, commands and replies, events, handshake and keep-alive between the terminal and the CH32 | [docs/en/hubp-serial.md](./docs/en/hubp-serial.md) | [docs/zh-CN/hubp-serial.md](./docs/zh-CN/hubp-serial.md) |
| C3 radio companion extensions: custom variables (`radio.rxgain`, `gps*`, ...), scoped text send, default radio parameters and transmit power limit | [docs/en/companion-extensions.md](./docs/en/companion-extensions.md) | [docs/zh-CN/companion-extensions.md](./docs/zh-CN/companion-extensions.md) |

## Related repositories

- [hubo-meshlora-c3](https://github.com/hubosmart/hubo-meshlora-c3): firmware of the MeshLoRa C3 radio.
- [hubo-wadamesh](https://github.com/hubosmart/hubo-wadamesh): firmware of the Hubo S3 terminal.
- [hubo-backpack-spec](https://github.com/hubosmart/hubo-backpack-spec): interface specification for 30-Pin backpacks.

## Tools

`python tools/check_lang_sync.py .` checks that `docs/en` and `docs/zh-CN` contain the same file names.

## License

[CC BY 4.0](./LICENSE). When you reuse this material, give credit as: `Hubosmart, Hubo-Mesh protocol specifications`.

The specifications are provided as is, and nothing here is a quality or compliance guarantee.
