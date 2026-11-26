#!/usr/bin/env python3
"""
AH-P05 handshake test.

Sends the unlock handshake captured from the PrinterMate app, shows every
printer reply, and can print a test pattern.

    python ahp05_handshake_test.py --print                  # handshake + test print
    python ahp05_handshake_test.py --no-handshake --print   # control test (expect no print)
    python ahp05_handshake_test.py --address AA:BB:CC:DD:EE:FF --print

Requires: pip install bleak
Turn off Bluetooth on any phone that is connected to the printer first.
"""
import argparse, asyncio, time
from datetime import datetime
from bleak import BleakClient, BleakScanner

WRITE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ffe2-0000-1000-8000-00805f9b34fb"
CHALLENGE = bytes.fromhex("5a1a829493c1fb9a7eeaf9a4")
EXPECT_1A = bytes.fromhex("5a1a162a2430a5c6be60f9a4")
TOKEN_1B = bytes.fromhex("5a1b152a3f54697e7bf70000")

T0 = time.monotonic(); LOG = []
def log(m):
    line = f"[{time.monotonic() - T0:8.3f}s] {m}"; print(line, flush=True); LOG.append(line)
hx = lambda b: b.hex(" ")
def ctrl(cmd, *p):
    pkt = bytes([0x5A, cmd, *p]); return pkt + bytes(12 - len(pkt))
def status(v):
    if len(v) >= 8 and v[:2] == b"\x5a\x02":
        return "  [status: " + {0x23: "idle", 0x30: "PRINTING", 0x00: "transition"}.get(v[5], f"?{v[5]:02x}") + "]"
    return "  [PRINT FINISHED]" if v[:2] == b"\x5a\x06" else ""

class Printer:
    def __init__(self, c): self.c = c; self.q = asyncio.Queue()
    def on_notify(self, _h, d):
        d = bytes(d); log(f"<- {hx(d)}{status(d)}"); self.q.put_nowait(d)
    async def send(self, pkt, label=""):
        log(f"-> {hx(pkt)}  {label}"); await self.c.write_gatt_char(WRITE_UUID, pkt, response=False)
    async def wait_for(self, prefix, timeout=3.0):
        end = time.monotonic() + timeout
        while (left := end - time.monotonic()) > 0:
            try: d = await asyncio.wait_for(self.q.get(), left)
            except asyncio.TimeoutError: return None
            if d.startswith(prefix): return d
        return None

async def connect(addr):
    for a in range(1, 4):
        log(f"Scanning for {addr or 'AH-P05'} (attempt {a}/3)...")
        dev = await (BleakScanner.find_device_by_address(addr, timeout=10) if addr else
                     BleakScanner.find_device_by_filter(lambda d, ad: (d.name or "").upper().startswith("AH-P05"), timeout=10))
        if not dev: log("Printer not found. Is it on, and is the phone disconnected?"); continue
        c = BleakClient(dev)
        try: await c.connect(timeout=15); log(f"Connected to {dev.address}."); return c
        except Exception as e: log(f"Connect failed: {type(e).__name__}: {e}"); await asyncio.sleep(2)
    return None

def pattern(rows=320):
    bm = bytearray()
    for y in range(rows):
        bits = [1 if (x < 3 or x > 92 or y < 3 or y > rows - 4) or (((x + y) // 8) % 2 == 0 and 10 < x < 86 and 10 < y < rows - 10) else 0 for x in range(96)]
        for b in range(12): bm.append(int("".join(map(str, bits[b * 8:b * 8 + 8])), 2))
    return [bytes([0x55, i >> 8, i & 0xFF]) + bm[i * 96:(i + 1) * 96] + b"\x00" for i in range(len(bm) // 96)]

async def run(a):
    c = await connect(a.address)
    if not c: log("RESULT: could not connect."); return
    p, verdict = Printer(c), []
    try:
        await c.start_notify(NOTIFY_UUID, p.on_notify); await asyncio.sleep(1.0)
        if not a.no_handshake:
            await p.send(CHALLENGE, "1a challenge"); r = await p.wait_for(b"\x5a\x1a")
            verdict.append("1a: NO REPLY" if r is None else "1a: reply IDENTICAL to capture" if r == EXPECT_1A else f"1a: reply DIFFERENT -> {hx(r)}")
            await p.send(TOKEN_1B, "1b token"); r = await p.wait_for(b"\x5a\x1b")
            verdict.append("1b: NO REPLY" if r is None else f"1b: ACCEPTED -> {hx(r)}" if r[2] == 1 else f"1b: NOT accepted -> {hx(r)}")
        else: verdict.append("handshake: SKIPPED (control test)")
        for pkt, pre, name in [(ctrl(0x0C, 3), b"\x5a\x0c", "0c 03"), (ctrl(0x01), b"\x5a\x01", "device info"), (ctrl(0x0C, a.level), b"\x5a\x0c", f"0c {a.level:02x}")]:
            await p.send(pkt, name); await p.wait_for(pre)
        if a.print:
            pk = pattern(); n = len(pk)
            await p.send(ctrl(0x04, n >> 8, n & 0xFF, 0, 1), "job start"); await p.wait_for(b"\x5a\x04")
            for x in pk: await c.write_gatt_char(WRITE_UUID, x, response=False); await asyncio.sleep(0.005)
            log(f"Sent {n} data packets; waiting for 5a 06...")
            done = await p.wait_for(b"\x5a\x06", timeout=a.done_timeout)
            await p.send(ctrl(0x04, n >> 8, n & 0xFF, 1, 1), "job end"); await p.wait_for(b"\x5a\x04")
            verdict.append("print: PRINTED (got 5a 06)" if done else "print: FAILED (no 5a 06 - data discarded)")
        else: await asyncio.sleep(5)
    finally:
        try: await c.disconnect(); log("Disconnected.")
        except Exception: pass
    log("SUMMARY"); [log("  " + v) for v in verdict]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="AH-P05 unlock handshake test")
    ap.add_argument("--address", help="printer BLE address (default: first device named AH-P05)")
    ap.add_argument("--print", action="store_true"); ap.add_argument("--no-handshake", action="store_true")
    ap.add_argument("--level", type=int, default=6, choices=range(1, 7)); ap.add_argument("--done-timeout", type=float, default=20)
    a = ap.parse_args()
    try: asyncio.run(run(a))
    finally:
        fn = f"ahp05_test_{datetime.now():%Y%m%d_%H%M%S}.log"; open(fn, "w").write("\n".join(LOG) + "\n"); print(f"\nLog saved to {fn}")
