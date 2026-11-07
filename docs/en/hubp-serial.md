> Translated from the Chinese version; if they differ, the Chinese version prevails.

# hubp Serial Protocol Specification

This document specifies the wire format and host-side behavior of the hubp serial protocol between the Hubo S3 terminal (host) and the CH32 coprocessor on the baseboard (device). It describes the wire protocol only, not the internals of the CH32 firmware.

## 1. Overview and Roles

- **Host**: the Hubo S3 terminal (ESP32-S3). It sends commands and receives replies and events.
- **Device**: the CH32 coprocessor. It handles the keyboard matrix, wheel and other input, answers commands, and pushes events on its own initiative.
- The protocol is a line-oriented ASCII text protocol with three kinds of frames: commands (host to device), replies (device to host), and events (device to host, unsolicited).
- Only one command is in flight at a time: after sending a command the host waits for the reply with the same sequence number; events that arrive meanwhile are handled as usual.

## 2. Physical Layer

Physical-layer parameters are outside the protocol and are decided by the implementation. The table shows how the reference implementation (the Hubo S3 terminal) wires them; third-party implementations may choose their own UART, pins and baud rate:

| Item | Reference implementation |
| --- | --- |
| UART | UART1, 8 data bits, no parity, 1 stop bit, no hardware flow control |
| Baud rate | 115200 |
| Host TX / RX | GPIO43 / GPIO44 |
| Interrupt line (optional) | GPIO46, host input with pull-up, falling-edge triggered |

The interrupt line is optional; the protocol does not require it:

- When an interrupt line is configured, as used by the reference implementation, the device pulls it low while it has events waiting; when the host sees it low, it drains the events with `HID:EVT:READ` (see section 5.2).
- Without an interrupt line the host relies on events pushed by the device. If the device capabilities do not include `EVT:PUSH` (see section 5.1), the host polls `HID:EVT:READ` every 20 ms.

## 3. Frame and Line Format

### 3.1 Lines

- A frame is one line of text terminated by a line feed `\n` (0x0A).
- Carriage returns `\r` (0x0D) are ignored on receive; empty lines are ignored.
- A line (excluding the line feed) is at most 127 bytes (the buffer `HUBP_PROTOCOL_LINE_MAX` is 128 bytes including the terminating NUL). An over-long line is discarded entirely, receiving resumes only after the next `\n`, and no frame is produced.
- Lines that match none of the formats below are silently ignored and produce no frame.
- Bytes may arrive fragmented or merged in any way: the parser is fed byte by byte and emits a frame only on `\n` (see the example session in section 9).

### 3.2 Command frame (host to device)

```
#NN:<command>\n
```

- `NN`: two-digit decimal sequence number, `00` to `99`; the host increments it for every command and wraps from 99 to 00.
- `<command>`: ASCII text, shorter than 96 bytes; otherwise the host does not send it.
- Example: `#07:SYS:PING\n`

### 3.3 Reply frame (device to host)

```
#NN:ACK:<body>\n       success
#NN:ERR:<body>\n       failure
```

- `NN` is the sequence number of the command being answered. The host only accepts a reply whose number equals that of the command in flight; replies with other numbers are ignored.
- `<body>` is the reply content; the host extracts it as is and imposes no further syntax (the body of each command is described in section 5).
- Examples: `#07:ACK:SYS:PING:PONG\n`, `#03:ERR:E102:UNKNOWN\n`

### 3.4 Event frame (device to host)

```
!EVT:<body>\n
```

Events are pushed by the device on its own initiative; they carry no sequence number and need no reply. The body format is in section 6.

## 4. Frame Types

The reference implementation classifies parse results into four `HUBP_FRAME_*` types:

| Enum | Meaning |
| --- | --- |
| `HUBP_FRAME_INVALID` | Invalid/unrecognized (value 0). The parser never emits this type; it is only the zero-value placeholder. |
| `HUBP_FRAME_ACK` | Success reply, from a `#NN:ACK:` line; carries a sequence number and a body. |
| `HUBP_FRAME_ERROR` | Failure reply, from a `#NN:ERR:` line; carries a sequence number and a body. |
| `HUBP_FRAME_EVENT` | Event, from a `!EVT:` line; no sequence number, body only. |

## 5. Commands and Replies

The table lists all commands used by the reference implementation (13 in total). All are sent from host to device and answered with ACK or ERR.

| Command | Purpose | Use in the reference implementation |
| --- | --- | --- |
| `SYS:INFO` | Query firmware information | Handshake step 1 |
| `SYS:CAPS` | Query capabilities | Handshake step 2 |
| `SYS:DETECT` | Detection | Handshake step 3; failure does not abort the handshake |
| `SYS:MODE:KB` | Switch to keyboard mode | Handshake step 4 |
| `SYS:MODE:IDLE` | Switch to idle mode | Defined, unused by the reference implementation |
| `SYS:PING` | Keep-alive | Once per second; reply body `SYS:PING:PONG` |
| `HID:KEY:SCAN:ON` | Enable key scanning and reporting | Handshake step 5; fuse recovery |
| `HID:KEY:SCAN:OFF` | Disable key scanning and reporting | Defined, unused by the reference implementation |
| `HID:KEY:MODE:ACTIVE` | Put key reporting in active mode | Handshake step 6 (only if the device supports `EVT:PUSH`); fuse recovery |
| `HID:KEY:MODE:SLEEP` | Put key reporting in sleep mode | Called by the host application on demand |
| `HID:KEY:RAWRESET` | Reset raw-key state | Defined, unused by the reference implementation |
| `HID:KEY:RAW:<n>` | Prefix command with a key-number argument (`<n>` is the decimal key number) | Defined, unused by the reference implementation |
| `HID:EVT:READ` | Take one queued event | See section 5.2 |

Notes:

- This document only specifies the ACK bodies that can be confirmed in code (below). For the other commands the ACK body, and the table of ERR error codes, are not parsed by the reference implementation and are **not specified at the protocol level**. The only ERR example in the reference implementation is `E102:UNKNOWN` (from the test case); it is presumably "unknown command", but no error-code table is given in the code.
- The host treats every command the same way: ACK is success, ERR is failure, and no reply within the timeout is a timeout.

### 5.1 Handshake: `SYS:INFO`, `SYS:CAPS`, `SYS:DETECT`

The handshake sends the following commands in order, each with a 500 ms timeout:

1. `SYS:INFO`. The host extracts two fields from the reply body (fields are separated by `:`):
   - `:FW=<firmware version>`: the host keeps at most 15 characters.
   - `:PROTO=<protocol version>`: the host keeps at most 7 characters.
   - The body may also carry a `SKU=<id>` field, which decides whether the device configures the keyboard matrix as 4x11 (SKU1) or 4x4 (SKU2). The reference implementation only logs it and does not parse it. The order of the fields is not specified.
2. `SYS:CAPS`. The host looks for capability markers as substrings of the reply body:
   - Contains `EVT:PUSH`: the device pushes events (`!EVT:`) on its own.
   - Contains `KEY:RELEASE`: the device reports key release events.
   - Contains `WHEEL:1`: the device has a wheel.
   - The body may carry other markers such as `BL:1`, whose meaning is defined by the implementation; the reference implementation only logs them.
3. `SYS:DETECT`: the reply is only logged; failure does not abort the handshake.
4. `SYS:MODE:KB`.
5. `HID:KEY:SCAN:ON`.
6. If CAPS contained `EVT:PUSH`, then `HID:KEY:MODE:ACTIVE`.

If any required step (1, 2, 4, 5, 6) fails the handshake fails, and the reference implementation retries after 100 ms. After all steps succeed the host considers the device online and starts keep-alive.

Before the handshake the reference implementation also sends `\n\n\nPING\n` to flush stray characters from the line and wake older devices. This is not part of the protocol; a device should ignore lines it cannot recognize (see section 3.1).

### 5.2 Reading events: `HID:EVT:READ`

- Reply body `HID:EVT:NONE`: no event is queued.
- Otherwise the reply body is `HID:EVT:<event body without the HID: prefix>`, for example `HID:EVT:KEY:K01:Q:PRESS:T=123`. The host prepends `HID:` to restore the same event body as a pushed event, `HID:KEY:K01:Q:PRESS:T=123`.
- If the body is neither `HID:EVT:NONE` nor starts with `HID:EVT:`, the host treats the reply as invalid.
- The host reads at most 64 events in a row and stops at `HID:EVT:NONE`. Each read command has a 300 ms timeout.

The same event may be both pushed and left in the queue to be pulled; the host drops duplicates with a de-duplication ring (see section 6.4).

### 5.3 Keep-alive: `SYS:PING`

While online, the host sends `SYS:PING` once per second (300 ms timeout). With no reply the host considers the device offline and handshakes again.

## 6. Events

The event body (the part after `!EVT:`) comes in three kinds.

### 6.1 Key events

```
HID:KEY:K<nn>:<name>:PRESS[:T=<ms>]
HID:KEY:K<nn>:<name>:RELEASE[:T=<ms>]
```

- `<nn>`: key number, decimal, 1 to 44; events out of range are discarded.
- `<name>`: for example `Q`, `FN`, `T`, `WHL_UP` (values seen in the test cases); the host does not parse the name and uses only the key number. The full list of key names is not specified at the protocol level.
- Action: the body ends with `:PRESS` or `:RELEASE`, or contains `:PRESS` / `:RELEASE` before `:T=`.
- `T=<ms>`: device timestamp in decimal milliseconds, optional. Older devices omit it, in which case the host treats the timestamp as 0.

### 6.2 Wheel events

```
HID:WHEEL:UP:PRESS|RELEASE[:T=<ms>]
HID:WHEEL:DOWN:PRESS|RELEASE[:T=<ms>]
HID:WHEEL:PUSH:PRESS|RELEASE[:T=<ms>]
```

The reference implementation maps the three directions to fixed internal key codes: `UP` is 11 (scroll delta -1), `DOWN` is 22 (delta +1), and `PUSH` (pressing the wheel) is 33.

### 6.3 System events

- `SYS:EVT_OVERFLOW:<n>`: the device event queue overflowed and `n` events were lost.
- `SYS:BOOT:...`: the device has just started or reset. On receiving it the host considers the device offline and handshakes again.
- `SYS:RESET:IDLE_TIMEOUT`: after the device received no host data for a period (3 seconds according to a code comment), it disables key reporting, returns to keyboard mode, and emits this event. On receiving it the host must resend `HID:KEY:SCAN:ON` (and `HID:KEY:MODE:ACTIVE` if the device supports `EVT:PUSH`) to resume reporting. This is why the host must keep sending keep-alive traffic.
- Other events starting with `SYS:`: the reference implementation only logs them; their body format is not specified.

### 6.4 Event body length, normalization and de-duplication

- An event body is at most 63 bytes (`HUBP_EVENT_BODY_MAX` is 64 including the terminating NUL).
- Normalization: if an event body starts with `KEY:` or `WHEEL:` (the `HID:` namespace is missing), `HID:` may be prepended so that the push and pull paths yield the same form. The reference implementation provides this normalization function and covers it with a test case; its push receive path currently uses the body after `!EVT:` as is and does not call it, so a device should send the complete event body with `HID:` directly after `!EVT:`.
- De-duplication: only event bodies that carry a `:T=` timestamp are de-duplicated, with a ring of 64 entries; a body byte-identical to one in the ring is a duplicate and is dropped. Legacy bodies without `:T=` are never de-duplicated (identical content may be the next real key press).

## 7. Errors and Timeouts

| Situation | Host handling |
| --- | --- |
| No reply to a command | Timeout; the caller decides whether to retry. Handshake commands time out after 500 ms, `HID:EVT:READ` and `SYS:PING` after 300 ms |
| ERR reply | The command failed; the body is handed to the caller as is |
| Reply sequence number does not match the command in flight | Ignored; keep waiting |
| Line too long, unrecognized, or not ACK/ERR/EVT | Silently dropped; later lines are unaffected |
| Keep-alive fails | Considered offline; handshake again |
| `SYS:BOOT:` received | Considered offline; handshake again |
| `SYS:RESET:IDLE_TIMEOUT` received | Resend `HID:KEY:SCAN:ON` (and `HID:KEY:MODE:ACTIVE` depending on capabilities) |
| Event parse failure (key number out of range, missing action, etc.) | The event is dropped |
| Host local event queue (64 entries) full | New events are dropped; the next read first returns an overflow notice and the queue is cleared so the upper layer can reset modifier-key state |

The overall handshake wait limit (`hubp_client_handshake` in the reference implementation) is 6 seconds.

## 8. Versioning and Compatibility

- The device reports the protocol version in the `:PROTO=` field of `SYS:INFO` and the firmware version in `:FW=`. The value space and evolution rules of the version numbers are not specified in the code.
- Capabilities are negotiated through `SYS:CAPS` (section 5.1): `EVT:PUSH`, `KEY:RELEASE`, `WHEEL:1`. The host should decide its behavior by capability, not by version number.
- Older devices: for a device without `EVT:PUSH` the host polls; for event bodies without a `:T=` timestamp the host does not de-duplicate.

## 9. Example Sessions

The examples come from the reference implementation's test cases. `>` is sent by the host, `<` by the device.

**Fragmentation and merging.** The byte stream delivers one event in two pieces, and a reply arrives in the same read; the parser emits two frames:

```
< !EVT:HID:KEY:K01:Q:PRE            (first piece, no line feed, no frame)
< SS:T=123\n#07:ACK:SYS:PING:PONG\n (second piece)
```

Result:

- an event frame, body `HID:KEY:K01:Q:PRESS:T=123`
- a reply frame (ACK), sequence 7, body `SYS:PING:PONG`

**Over-long line recovery.** 140 bytes with no line feed: the parser enters the dropping state and only recovers at the next line feed. A valid line that follows is parsed normally:

```
< XXXX... (140 X characters)\n      (whole line discarded, no frame)
< #03:ERR:E102:UNKNOWN\n            (ERROR frame, sequence 3, body E102:UNKNOWN)
```

**Event parsing:**

| Event body | Result |
| --- | --- |
| `HID:KEY:K37:FN:RELEASE:T=456` | key 37, release, device timestamp 456 ms |
| `HID:WHEEL:UP:PRESS:T=500` | wheel up, internal code 11, delta -1, press |
| `HID:WHEEL:DOWN:RELEASE:T=501` | wheel down, internal code 22 |
| `HID:WHEEL:PUSH:PRESS:T=502` | wheel push, internal code 33 |
| `SYS:EVT_OVERFLOW:9` | overflow notice, 9 events lost |
| `HID:KEY:K05:T:PRESS` | key 5, press, no timestamp (timestamp 0) |

**De-duplication:**

```
HID:KEY:K01:Q:PRESS:T=123    accepted
HID:KEY:K01:Q:PRESS:T=123    duplicate, dropped
HID:KEY:K01:Q:RELEASE:T=124  accepted
(after 64 other events are accepted, the ring is overwritten)
HID:KEY:K01:Q:PRESS:T=123    accepted again
HID:KEY:K01:Q:PRESS          legacy (no T=), always accepted
```

**Normalization:**

```
KEY:K05:T:PRESS:T=260609    ->  HID:KEY:K05:T:PRESS:T=260609
WHEEL:UP:RELEASE:T=260700   ->  HID:WHEEL:UP:RELEASE:T=260700
SYS:EVT_OVERFLOW:3          ->  SYS:EVT_OVERFLOW:3 (unchanged)
```

**A typical command round trip** (illustrative; the sequence number and reply body depend on the actual device):

```
> #07:SYS:PING\n
< #07:ACK:SYS:PING:PONG\n
```

## Sources

This specification is derived from the following files of the reference implementation; every clause can be traced to them:

- Reference implementation: `hubp_protocol.h`: line-length constant, `HUBP_FRAME_*` enum, parser and de-duplication structures
- Reference implementation: `hubp_protocol.c`: line parsing (`!EVT:`, `#NN:ACK:`, `#NN:ERR:`), event parsing, normalization, de-duplication
- Reference implementation: `hubp_client.h`: command constant table, event structure, public interface, `HUBP_EVENT_BODY_MAX`, `HUBP_EVENT_DEDUPE_DEPTH`
- Reference implementation: `hubp_client.c`: sequence numbers and command framing, handshake flow, timeouts, keep-alive, `SYS:RESET:IDLE_TIMEOUT` recovery, event pulling, default UART and interrupt-line configuration
- Reference implementation: `test_hubp_protocol.c`: example sessions
- Reference implementation: `app_main.cpp` (terminal application entry): the actual UART and pin configuration (UART1, GPIO43/44/46, 115200)
