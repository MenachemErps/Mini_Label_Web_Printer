# AH-P05 Label Studio

Design and print labels on the **XenGro AH-P05** Bluetooth label printer (12 mm tape, 96-dot head) from your browser, with no phone app needed.

**▶ Open the app:** `https://<your-username>.github.io/<repo-name>/` *(replace with your GitHub Pages link)*

> Not affiliated with XenGro or the PrinterMate app. Made with AI for a printer I own. Use at your own risk.

## Features

- **Editor:** text and fonts (including web fonts), emoji, images, QR codes, Code 128 barcodes, drag, resize and rotate, undo
- **Outline icons:** search thousands of free open-source icons (Tabler, Lucide, Phosphor, Iconoir) through the Iconify API, plus a built-in offline set
- **Shapes:** boxes, rounded boxes, pills, circles, lines, arrows, speech bubbles, triangles and stars
- **Cable flag builder:** enter the cable diameter and it sizes the wrap zone and puts the text on both ends
- **Batch printing:** import a CSV or paste from Excel, use `{1}`, `{2}`… for the columns, and preview every label before printing
- **Share links:** the whole design is packed into the link, so others open the exact label
- **Install as an app:** works offline after the first visit (Edge or Chrome → Install)
- **Themes:** Vibe (dark teal, default), Night and Light
- Templates, saved labels, counters and dates (`{n:3}`, `{date+7}`), mirror and invert, PNG export, diagnostics log

## Requirements

- **Microsoft Edge or Google Chrome** on Windows, macOS, Linux or Android (Web Bluetooth). Firefox, Safari and all iPhone browsers can design labels but can't print.
- The printer can only have **one connection at a time**, so turn off Bluetooth on a phone that is connected to it.

## Files

| File | What it is |
|---|---|
| `index.html` | The whole app (one file) |
| `manifest.webmanifest`, `sw.js`, `icon-*.png` | Let the app be installed and work offline |
| `ahp05_handshake_test.py` | Python test tool (`pip install bleak`) |

## The interesting part: the unlock handshake

At first, prints from the PC worked only sometimes. When they failed, the printer answered every command and accepted all the image data, then **silently discarded it**. A Bluetooth capture of the PrinterMate app showed what was missing: a two-step unlock it sends every time it connects.

| Step | Direction | Bytes |
|---|---|---|
| 1 | app → printer | `5a 1a 82 94 93 c1 fb 9a 7e ea f9 a4` |
| 2 | printer → app | `5a 1a 16 2a 24 30 a5 c6 be 60 f9 a4` |
| 3 | app → printer | `5a 1b 15 2a 3f 54 69 7e 7b f7 00 00` |
| 4 | printer → app | `5a 1b 01 …` (`01` = accepted) |

Tested on one printer: with the handshake it printed 2 out of 2 times (including after a power cycle). Without it, 0 out of 3 printed.

**Is it a replay? Yes.** The tools resend the exact bytes from one capture. It works because the printer adds no randomness of its own: the same challenge always gets the same answer. It looks like an "is this the official app?" check rather than real security.

**Help wanted:** if you own an AH-P05, please open an issue saying whether it worked. The bytes may be tied to each printer's Bluetooth address, or a firmware update could break them.

Clues for anyone who wants to work out the real algorithm:
- The last two challenge bytes (`f9 a4`) come back at the end of the reply.
- The first six token bytes count up in steps of `0x15` (`15 2a 3f 54 69 7e`).
- The LX-D02's CRC16-XMODEM handshake did not match.

## Protocol reference

| Service | Characteristic | Use |
|---|---|---|
| `ffe6` | `ffe1` | Write (without response) |
| `ffe6` | `ffe2` | Notify |
| `ff12` | `ff14`/`ff15` | Looks like firmware update. **Don't write here.** |

- **Control packets:** 12 bytes, `5A <cmd> <payload, zero padded>`
- **Image data:** 100 bytes, `55 <idx hi> <idx lo> <96 bytes = 8 rows × 12 bytes> 00`
- **Image format:** 96 px wide, 1 bit per pixel, MSB first, 1 = black, rotated 90° clockwise. 40 mm = 320 rows = 40 packets.

**Sequence:**
1. Enable notifications.
2. Handshake (above).
3. `5a 0c 03`, then `5a 01`, then `5a 0c <1-6>`.
4. `5a 04 <n hi> <n lo> 00 01` (job start).
5. Send the data packets.
6. Wait for `5a 06` (finished).
7. `5a 04 <n hi> <n lo> 01 01` (job end).

**Status `5a 02`:** byte 5 = `23` idle, `30` printing, `00` busy. Use `5a 06` to confirm a print, because short prints can finish between status updates.

## Security and privacy

- **Hosting:** the app is static files on GitHub Pages, served over HTTPS. There is no server, no account and no tracking.
- **Your data stays in your browser:** labels, settings and saved designs are only stored on your device.
- **Outside connections, only when you use these features:**
  - Icon search contacts `api.iconify.design` (or its backup hosts `api.simplesvg.com` / `api.unisvg.com`).
  - Web fonts load from Google Fonts.
  - Nothing else is contacted, and a Content-Security-Policy blocks anything else.
- **Bluetooth:** the browser only connects to the printer you pick in its own pop-up window.
- **Share links:** the design is stored after the `#`, which browsers never send to servers. Anyone who has a link can see what's on the label, so don't share labels that contain passwords. Links you open are checked before loading, and only plain images are accepted.

## How to capture the app's traffic (Android)

1. Developer options → **Bluetooth HCI snoop log** → Enabled. Turn Bluetooth off and on.
2. Use PrinterMate.
3. Developer options → **Take bug report** (Full).
4. In the zip, open the largest `btsnoop_hci*` file in Wireshark, filter `btatt`, then use File → Export Packet Dissections → As Plain Text.

## Related projects

LX-D02 (`amahlaka/LX-D02`), picoprint (`bigtower17/picoprint`), blethermal (XenGro AH-M2), printer-driver-funnyprint.
