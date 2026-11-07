> Translated from the Chinese version; if they differ, the Chinese version prevails.

# C3 Radio Companion Protocol Extensions

The Hubo S3 terminal connects to the MeshLoRa C3 radio over BLE and uses the standard MeshCore companion protocol. This document specifies only what the C3 radio firmware adds on top of the standard protocol: custom variables, a scoped text-send command, and the default radio parameters and transmit power limit. For the standard commands themselves (contacts, messages, channels, etc.) refer to the MeshCore companion protocol documentation.

## 1. Standard Commands Used

Custom variables reuse three codes of the standard MeshCore companion protocol; no new command codes are introduced:

| Name | Code | Direction | Description |
| --- | --- | --- | --- |
| `GET_CUSTOM_VARS` | 40 | host to radio | Read all custom variables |
| `SET_CUSTOM_VAR` | 41 | host to radio | Write one custom variable |
| `RESP_CUSTOM_VARS` | 21 | radio to host | Reply to `GET_CUSTOM_VARS` |

Standard reply codes: `RESP_OK` = 0, `RESP_ERR` = 1 (followed by a 1-byte error code). Error codes referred to in this document:

| Error code | Name |
| --- | --- |
| 1 | `UNSUPPORTED_CMD` |
| 2 | `NOT_FOUND` |
| 3 | `TABLE_FULL` |
| 4 | `BAD_STATE` |
| 5 | `FILE_IO_ERROR` |
| 6 | `ILLEGAL_ARG` |

### 1.1 Reading: `GET_CUSTOM_VARS`

Request frame:

```
[40]
```

Reply frame:

```
[21] "name:value,name:value,..."
```

- The first byte is 21, followed by ASCII text with no terminating NUL; the frame length is the text length plus 1.
- The text is a list of `name:value` pairs separated by `,`; `name` and `value` are separated by the first `:`.
- The fixed variables (`radio.rxgain`, `hubo.scope_tx`) always come first, followed by the variables provided by sensors.
- Before appending each sensor variable the radio checks the length of the text written so far; once it exceeds 140 bytes no further variables are appended, so with many variables the trailing ones may be missing.
- If reading `radio.rxgain` from the radio chip fails, the radio replies with an `ERR` frame (`BAD_STATE`) instead of `RESP_CUSTOM_VARS`.

Reply example (radio with GNSS, no fix yet):

```
radio.rxgain:1,hubo.scope_tx:1,gps:1,gps_interval:0,gps_fix:0,gps_sats:0,gps_nmea:37,gps_lat:,gps_lon:,gps_alt:
```

### 1.2 Writing: `SET_CUSTOM_VAR`

Request frame:

```
[41] "name:value"
```

- The frame is at least 4 bytes; `name` and `value` are separated by the first `:`; without a `:` the radio replies `ERR(ILLEGAL_ARG)`.
- Success replies `OK`; an unknown name, a read-only name or an invalid value replies `ERR(ILLEGAL_ARG)`.
- When the write succeeds and the variable must be persisted, the radio writes the preferences to storage first; if the storage write fails it rolls back and replies `ERR(FILE_IO_ERROR)`.

## 2. Custom Variables

The C3 radio provides the 10 variables in the table. The first 2 always exist; the 8 variables starting with `gps` exist only on radio firmware with a GNSS module (the GNSS edition) and do not appear on radios without GNSS.

| Name | Access | Values | Meaning |
| --- | --- | --- | --- |
| `radio.rxgain` | read/write | `0` or `1` (a single character; a write must be exactly this) | Radio receive gain mode (RX boosted gain). `1` is on. After a write the radio reads the setting back to confirm and saves it to preferences; on error it rolls back. |
| `hubo.scope_tx` | read-only | always `1` | The radio supports the scoped text-send command (section 4). |
| `gps` | read/write | `0` or `1` | GNSS switch; `1` powers the module and starts receiving NMEA sentences, `0` powers it off and clears the state. Default `0` (off at power-up). A written value counts as on if its first character is `1`; it is saved to preferences. |
| `gps_interval` | read/write | non-negative integer, seconds; limited to 0 to 86400 in preferences | Stored only, with no effect on behavior: once enabled the GNSS runs continuously and is not switched on a schedule. Default `0`. |
| `gps_fix` | read-only | `0` or `1` | Whether there is a valid fix (latest RMC status is A, or GGA quality indicator greater than 0). |
| `gps_sats` | read-only | non-negative integer | Number of satellites, taken from the GGA sentence. |
| `gps_nmea` | read-only | non-negative integer | Cumulative count of NMEA sentences with a correct checksum (modulo 10^9). Without a fix indoors it still shows that the GNSS serial link works. |
| `gps_lat` | read-only | decimal degrees, 6 decimal places, negative for south, e.g. `12.345678`; empty when there is no fix | Latitude. |
| `gps_lon` | read-only | decimal degrees, 6 decimal places, negative for west, e.g. `-98.765432`; empty when there is no fix | Longitude. |
| `gps_alt` | read-only | integer meters, may be negative; empty when there is no fix | Altitude (rounded to whole meters). |

Notes:

- An empty value is written `gps_lat:` (nothing after the colon) and is still a valid `name:value` pair.
- After the module is powered off (`gps` is `0`), `gps_fix`, `gps_sats` and `gps_nmea` return to 0 and the three position variables are empty.
- With a fix and the GNSS on, the radio also uses the latitude, longitude and altitude as the node's own position (for adverts and self info) and includes GPS in telemetry (when the requester has location permission).
- Writing any name not in the table replies `ERR(ILLEGAL_ARG)`.

## 3. How the Terminal Detects C3 Capabilities

After connecting, the terminal (Hubo S3) sends one `GET_CUSTOM_VARS` and derives capabilities from the reply:

| Capability | Rule |
| --- | --- |
| Receive gain available | `radio.rxgain` is present in the reply with value `0` or `1` |
| Scoped text send available | `hubo.scope_tx` has value `1` |
| GPS available | `gps` is present in the reply with value `0` or `1` |
| GPS on | `gps` is `1` |
| Has a fix | `gps_fix` is `1`; the position counts as available only if all three of `gps_lat`, `gps_lon`, `gps_alt` have values |

When GPS is available and on, the terminal re-reads `GET_CUSTOM_VARS` about every 2 seconds to refresh the fix state.

The terminal parses strictly: the whole reply is rejected (treated as unusable, none of its variables used) if any of the following occurs:

- The first byte is not 21, or the text contains a NUL byte.
- The value of `radio.rxgain`, `hubo.scope_tx`, `gps` or `gps_fix` is not a single character `0` or `1`.
- `gps_sats` or `gps_nmea` is not 1 to 9 plain decimal digits; `gps_sats` is greater than 255.
- A non-empty `gps_lat` / `gps_lon` is not decimal degrees: an optional minus sign, at most 3 integer digits, 1 to 6 decimal digits, absolute value at most 90 / 180; a non-empty `gps_alt` is not an integer of at most 6 digits (optional minus sign).
- Any of the above variables appears more than once.

Variable names not in the table are ignored by the terminal. Names must match in full: `gps` does not match `gps_interval`.

Variables the terminal writes:

- Receive gain: `[41] "radio.rxgain:0"` or `"radio.rxgain:1"` (15 bytes).
- GPS switch: `[41] "gps:0"` or `"gps:1"` (6 bytes).

## 4. Scoped Text Send (`hubo.scope_tx`)

When `hubo.scope_tx` is `1`, the radio supports an extension sub-command of standard companion command 54 (`SET_FLOOD_SCOPE_KEY`): send one channel text message with a flood scope specified for that message only, without changing the radio's default scope or stored configuration.

Request frame (26 to 176 bytes):

| Offset | Length | Meaning |
| --- | --- | --- |
| 0 | 1 | Command code 54 |
| 1 | 1 | Sub-command, fixed at 2 |
| 2 | 1 | Scope kind: 0 use the radio's default scope, 1 no scope (unscoped flood), 2 use the key given below |
| 3 | 16 | Scope key; must not be all zero when the kind is 2, otherwise fill with 0 |
| 19 | 1 | Reserved, must be 0 |
| 20 | 1 | Channel index; must be less than the radio's channel count |
| 21 | 4 | Send timestamp, little-endian 32-bit unsigned integer |
| 25 | N | Text, UTF-8, N is 1 to 151 bytes; must not contain NUL and must be valid UTF-8 |

Reply: success replies `OK`; invalid arguments (bad format, channel index, invalid text, or text too long once the node name is added) reply `ERR(ILLEGAL_ARG)`; a channel that does not exist replies `ERR(NOT_FOUND)`; a send failure such as a full send queue replies `ERR(TABLE_FULL)`. Whether it succeeds or fails, the radio restores its previous scope settings after handling the command.

## 5. Default Radio Parameters and Transmit Power Limit

Compile-time defaults of the C3 radio firmware:

| Parameter | Default |
| --- | --- |
| Frequency | 433.650 MHz |
| Bandwidth (BW) | 62.5 kHz |
| Spreading factor (SF) | 8 |
| Coding rate (CR) | 5 (that is, 4/5) |
| Transmit power | 10 dBm |
| Transmit power limit | 10 dBm |
| Radio chip | SX1268 (build default; see the variant table in the C3 README for each board) |

Radio constraints:

- Transmit power is limited by the standard command `SET_RADIO_TX_POWER` to -9 dBm up to the 10 dBm limit; anything outside replies `ERR(ILLEGAL_ARG)`. The limit is also reported in the standard self-info reply (`SELF_INFO`) through the "max transmit power" field (the 1 byte right after the current transmit power).
- Radio parameters (`SET_RADIO_PARAMS`) are validated before being applied: frequency 410 to 493 MHz, SF 5 to 12, CR 5 to 8, bandwidth one of 7.8, 10.4, 15.6, 20.8, 31.25, 41.7, 62.5, 125, 250, 500 kHz; transmit power -9 to 10 dBm. A failed validation replies `ERR(ILLEGAL_ARG)`.
- The defaults above are compile-time values; after the first boot the radio uses the current values stored in preferences.

## Sources

This specification is derived from the following files of the C3 radio firmware and the S3 terminal source:

- Reference implementation: `MyMesh.cpp` (C3 companion protocol implementation): command and reply code definitions, `GET_CUSTOM_VARS` / `SET_CUSTOM_VAR` handling, the scoped-text sub-command, transmit power and radio parameter handling, the transmit power field in `SELF_INFO`
- Reference implementation: `HuboGnss.h`, `HuboGnss.cpp`: names, value formats and behavior of the GNSS custom variables
- Reference implementation: `HuboNativeExtensions.h`: `radio.rxgain` write rules, frame parsing of the scoped-text sub-command
- Reference implementation: `HuboNmea.h`: the sentences that `gps_fix`, `gps_sats` and `gps_nmea` come from
- Reference implementation: `radio_settings.cpp`: valid ranges of the radio parameters
- Reference implementation: `CMakeLists.txt` (companion component): compile-time default radio parameters, transmit power limit, build condition of the GNSS variables
- Reference implementation: `HuboProtocolExtensions.h` (S3 terminal side): reply parsing rules and the frame formats the terminal writes
- Reference implementation: `HuboRemoteClient.cpp` (S3 terminal side): GPS refresh period
