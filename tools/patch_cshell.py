#!/usr/bin/env python3
"""Patch Die Hard: Nakatomi Plaza v1.04 so it doesn't hang at startup under Wine/Proton.

Bug: cshell.dll allocates its mission-list object (0x12a4 bytes) with operator new and the
constructor never initialises the mission counters at +0x1174/+0x1178/+0x117c. The main menu
reads them before the mission loader runs. On Windows the fresh heap block is zero; under
Wine it is recycled memory (e.g. a copy of the environment block), so the menu tries to
build ~1.6 billion entries and the game spins forever, eating RAM, with no window.

Fix: redirect the constructor's single call to a stub in the unused tail of .text that
zero-fills the object and then jumps to the original constructor.

Usage: patch_cshell.py <path to Nakatomi3.rez>   (patches in place, keeps a .orig backup)
"""
import shutil
import struct
import sys

BASE = 0x10000000
CALL_SITE = 0x100086DC   # e8 57 fa ff ff  call 0x10008138
CTOR = 0x10008138
STUB = 0x10069FA0        # inside .text slack (virtual size 0x68f96, raw size 0x69000)
OBJ_DWORDS = 0x12A4 // 4

ORIG_CALL = bytes.fromhex("e857faffff")


def rel32(src_next, dst):
    return struct.pack("<i", dst - src_next)


def build_stub():
    code = bytearray()
    code += b"\x57"                                   # push edi
    code += b"\x89\xf7"                               # mov edi, esi   (esi = this)
    code += b"\xb9" + struct.pack("<I", OBJ_DWORDS)   # mov ecx, 0x4a9
    code += b"\x31\xc0"                               # xor eax, eax
    code += b"\xfc"                                   # cld
    code += b"\xf3\xab"                               # rep stosd
    code += b"\x5f"                                   # pop edi
    code += b"\x89\xf1"                               # mov ecx, esi
    code += b"\xe9" + rel32(STUB + len(code) + 5, CTOR)  # jmp original constructor
    return bytes(code)


def main():
    rez = sys.argv[1]
    data = bytearray(open(rez, "rb").read())

    # cshell.dll is stored uncompressed inside the REZ; find it by its PE header + export name.
    dll_off = None
    pos = 0
    while True:
        pos = data.find(b"MZ", pos)
        if pos < 0:
            break
        pe = pos + struct.unpack_from("<I", data, pos + 0x3C)[0] if pos + 0x40 < len(data) else 0
        if 0 < pe < len(data) - 4 and data[pe:pe + 4] == b"PE\0\0":
            image_base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
            if image_base == BASE and data[pos + CALL_SITE - BASE:pos + CALL_SITE - BASE + 5] in (
                    ORIG_CALL, b"\xe8" + rel32(CALL_SITE + 5, STUB)):
                dll_off = pos
                break
        pos += 2
    if dll_off is None:
        sys.exit("cshell.dll with the expected code not found (wrong game version?)")

    call_at = dll_off + (CALL_SITE - BASE)
    stub_at = dll_off + (STUB - BASE)
    stub = build_stub()
    new_call = b"\xe8" + rel32(CALL_SITE + 5, STUB)

    if bytes(data[call_at:call_at + 5]) == new_call and bytes(data[stub_at:stub_at + len(stub)]) == stub:
        print("already patched")
        return
    if bytes(data[stub_at:stub_at + len(stub)]) != bytes(len(stub)):
        sys.exit("stub area is not empty, refusing to patch")

    shutil.copy2(rez, rez + ".orig")
    data[call_at:call_at + 5] = new_call
    data[stub_at:stub_at + len(stub)] = stub
    with open(rez, "r+b") as f:
        f.seek(call_at)
        f.write(new_call)
        f.seek(stub_at)
        f.write(stub)
    print(f"patched cshell.dll at REZ offset {dll_off} (backup: {rez}.orig)")


if __name__ == "__main__":
    main()
