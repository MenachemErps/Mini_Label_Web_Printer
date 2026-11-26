# AH-P05 Label Printer: print from Windows without the phone app

A small open project for printing to the **XenGro AH-P05** Bluetooth label printer (12 mm labels, 96-dot head) from a PC, without the PrinterMate phone app.

It includes:

- **AH-P05 Label Studio** (`AHP05_Label_Studio_v6.html`): a single HTML file that runs in Edge or Chrome and prints over Web Bluetooth. No install, no Python.
- **Protocol notes** (below) for anyone writing their own driver.

> Made with AI. Use at your own risk.

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

A Bluetooth capture of the PrinterMate app showed every time it connects, the app sends a two-step **unlock handshake** before printing:

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


## Known issues

- Edge may show the Bluetooth picker on every connection.
- Code 128 barcodes haven't been checked with a real scanner yet.
- Label length (40 mm) is assumed, not measured.

## Related projects

Similar printers with related protocols: LX-D02 (`amahlaka/LX-D02`), picoprint (`bigtower17/picoprint`), blethermal (XenGro AH-M2), and printer-driver-funnyprint.
