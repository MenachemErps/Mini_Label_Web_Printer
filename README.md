# AH-P05 Label Printer: print from Windows without the phone app

A small open project for printing to the **XenGro AH-P05** Bluetooth label printer (12 mm labels, 96-dot head) from a PC, without the PrinterMate phone app.

It includes:

- **AH-P05 Label Studio** (`AHP05_Label_Studio_v6.html`): a single HTML file that runs in Edge or Chrome and prints over Web Bluetooth. No install, no Python.
- **`ahp05_handshake_test.py`**: a small Python test script (uses `bleak`) that unlocks the printer and prints a test pattern.
- **Protocol notes** (below) for anyone writing their own driver.

> Not affiliated with XenGro or the PrinterMate app. Reverse-engineered for interoperability with a printer I own. Use at your own risk.

---

## Quick start (browser app)

1. Download `AHP05_Label_Studio_v6.html` and open it in **Microsoft Edge** or **Google Chrome** on Windows.
2. Make sure the printer is on and **not connected to your phone** (it only allows one connection at a time).
3. Design a label and press **Print**. Pick `AH-P05` in the Bluetooth window.

Features: text and fonts, emoji and symbols, images, QR codes, Code 128 barcodes, borders, date and counter tokens, copies and batches, templates, saved labels, PNG export, and a diagnostics log.

## Quick start (Python test)

```
pip install bleak
python ahp05_handshake_test.py --print
```

Prints a striped test pattern and shows every packet. `--no-handshake --print` shows what happens without the unlock (the job is silently discarded).

---

## The interesting part: the "silent discard" and the unlock handshake

At first, prints from the PC worked only sometimes. When they failed, the printer:

- answered every command normally,
- accepted the job start and all the image data,
- stayed idle and **never printed**, with no error.

Prints only worked after the phone app had connected recently, which looked like a random bug.

A Bluetooth capture of the PrinterMate app showed what was missing. Every time it connects, the app sends a two-step **unlock handshake** before printing:

| Step | Direction | Bytes |
|---|---|---|
| 1 | app -> printer | `5a 1a 82 94 93 c1 fb 9a 7e ea f9 a4` |
| 2 | printer -> app | `5a 1a 16 2a 24 30 a5 c6 be 60 f9 a4` |
| 3 | app -> printer | `5a 1b 15 2a 3f 54 69 7e 7b f7 00 00` |
| 4 | printer -> app | `5a 1b 01 00 00 00 00 00 00 00 00 00` (`01` = accepted) |

Without it the printer ignores print data. With it, printing works every time.

Tested on one printer:

| Test | Result |
|---|---|
| Handshake, then print | Printed (2 out of 2, including after a power cycle) |
| No handshake, then print | Discarded (3 out of 3) |

### Is this a replay?

**Yes.** These tools resend the exact bytes the app sent in one capture. I didn't work out how the app generates them.

It works because the printer adds no randomness of its own: the same challenge got the identical reply every time, even after a power cycle. So a recorded exchange keeps working. It looks like a simple "is this the official app?" check rather than real security.

### Help wanted

**If you own an AH-P05, please test it and open an issue with the result.** I've only tested one printer, so I don't know if these bytes work on other units. The token might be tied to each printer's Bluetooth address, and a firmware update could also break the replay.

If it doesn't work on yours, a capture from your phone would help. Steps are below.

Clues for anyone who wants to work out the real algorithm:

- The last two challenge bytes (`f9 a4`) are repeated at the end of the printer's reply.
- The first six token bytes count up in equal steps: `0x15 x 1..6` (`15 2a 3f 54 69 7e`). Earlier sessions used different step sizes.
- The similar LX-D02 printer uses a CRC16-XMODEM-based handshake (`0a`/`0b`). That method did not match this one.

---

## Protocol reference

**Bluetooth LE services**

| Service | Characteristic | Use |
|---|---|---|
| `ffe6` | `ffe1` | Write (without response) |
| `ffe6` | `ffe2` | Notify (status and replies) |
| `ff12` | `ff14` / `ff15` | Looks like firmware update. **Don't write here.** |

**Packets**

- Control: 12 bytes, `5A <cmd> <payload, zero padded>`
- Image data: 100 bytes, `55 <index hi> <index lo> <96 bytes = 8 rows x 12 bytes> 00`
- Image: 96 px wide, 1 bit per pixel, MSB first, 1 = black, rotated 90 degrees clockwise. One 40 mm label = 320 rows = 40 packets.

**Full print sequence**

1. Enable notifications on `ffe2`.
2. Unlock handshake (`5a 1a`, then `5a 1b`, wait for `5a 1b 01`).
3. `5a 0c 03`, `5a 01` (device info), `5a 0c <1-6>`. Wait for each echo.
4. `5a 04 <count hi> <count lo> 00 01`: job start.
5. Send all image packets (about 5 ms apart is fine).
6. Wait for `5a 06 ...`: printing finished (about 5 seconds).
7. `5a 04 <count hi> <count lo> 01 01`: job end.

**Status packet `5a 02 ...`** (about once a second): byte 5 = `23` idle, `30` printing, `00` busy. Byte 7 repeats the last `0c` value. Status can miss short prints, so use `5a 06` to confirm a print.

**Not yet known:** the exact meaning of the `0c` levels (probably darkness), multi-label jobs, other label lengths, and most status bytes.

---

## How to capture the app's Bluetooth traffic (Android)

1. Developer options -> **Bluetooth HCI snoop log** -> Enabled. Turn Bluetooth off and on.
2. Open PrinterMate, connect to the printer (print once if you like), then disconnect.
3. Developer options -> **Take bug report** -> Full. Copy the zip to your PC.
4. Find the largest `btsnoop_hci*` file (often under `FS/data/log/bt/` or `FS/data/misc/bluetooth/logs/`).
5. Open it in Wireshark, filter `btatt`, then File -> Export Packet Dissections -> As Plain Text.

## Known issues

- Edge may show the Bluetooth picker on every connection.
- Code 128 barcodes haven't been checked with a real scanner yet.
- Label length (40 mm) is assumed, not measured.

## Related projects

Similar printers with related protocols: LX-D02 (`amahlaka/LX-D02`), picoprint (`bigtower17/picoprint`), blethermal (XenGro AH-M2), and printer-driver-funnyprint.
