#!/usr/bin/env python3
"""Patch Die Hard: Nakatomi Plaza v1.04 lithtech.exe so input polling can't freeze the game under Wine/Proton.

Bug: each frame the engine reads DirectInput buffered data per device. For the mouse (device
flag +0x2fc) it reads ONE event per GetDeviceData call and repeats while a call returns any.
Wine's dinput keeps reporting one (empty) event for this mouse, so the loop never ends: the main
thread spins at 100% and no frame is ever rendered (black screen, GPU idle).

Fix: treat the mouse like every other device: read up to 64 events in one call per frame, and
never repeat. Real input still arrives; a misbehaving queue can no longer stall a frame.

Usage: patch_lithtech.py <path to lithtech.exe>   (patches in place, keeps a .orig backup)
"""
import shutil
import struct
import sys

PATCHES = [
    # 0x42f826: neg eax; sbb eax,eax; and al,0xc1; add eax,0x40  (count = flag ? 1 : 64)
    #        -> mov eax,0x40; nop x4                             (count = 64)
    (0x42F826, bytes.fromhex("f7d81bc024c183c040"), bytes.fromhex("b84000000090909090")),
    # 0x42fca1: je 0x42fcad (repeat only for flagged devices) -> jmp 0x42fcad (never repeat)
    (0x42FCA1, bytes.fromhex("740a"), bytes.fromhex("eb0a")),
]


def file_offset(data, va):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    count = struct.unpack_from("<H", data, pe + 6)[0]
    sections = pe + 24 + struct.unpack_from("<H", data, pe + 20)[0]
    rva = va - base
    for i in range(count):
        vsize, vaddr, rsize, raw = struct.unpack_from("<IIII", data, sections + 40 * i + 8)
        if vaddr <= rva < vaddr + max(vsize, rsize):
            return raw + rva - vaddr
    raise ValueError(f"{va:#x} not in any section")


def main():
    exe = sys.argv[1]
    data = bytearray(open(exe, "rb").read())
    todo = []
    for va, old, new in PATCHES:
        off = file_offset(data, va)
        cur = bytes(data[off:off + len(old)])
        if cur == new:
            continue
        if cur != old:
            sys.exit(f"unexpected bytes at {va:#x}: {cur.hex()} (wrong lithtech.exe version?)")
        todo.append((off, new))
    if not todo:
        print("already patched")
        return
    shutil.copy2(exe, exe + ".orig")
    with open(exe, "r+b") as f:
        for off, new in todo:
            f.seek(off)
            f.write(new)
    print(f"patched {len(todo)} site(s) in {exe} (backup: {exe}.orig)")


if __name__ == "__main__":
    main()
