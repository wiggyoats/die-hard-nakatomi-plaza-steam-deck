#!/usr/bin/env python3
"""Adds (or replaces) one non-Steam shortcut that runs a Windows exe under a given Proton.
Run ON THE DECK with Steam closed (Steam rewrites both files from memory when it exits).

  add_proton_shortcut.py NAME EXE STARTDIR "LAUNCH OPTIONS" [COMPAT_TOOL=proton_experimental]

Writes userdata/*/config/shortcuts.vdf (binary VDF) and the CompatToolMapping in
config/config.vdf (text VDF), backing both up as *.before-<name-slug> first. Re-running
replaces the entry with the same name instead of duplicating it."""
import binascii
import glob
import os
import re
import shutil
import struct
import sys

MAP, STR, INT, END = 0, 1, 2, 8
STEAM = os.path.expanduser('~/.local/share/Steam')


def parse(data, i=0):
    out = {}
    while True:
        kind = data[i]; i += 1
        if kind == END:
            return out, i
        end = data.index(0, i); key = data[i:end].decode('utf-8'); i = end + 1
        if kind == MAP:
            out[key], i = parse(data, i)
        elif kind == STR:
            end = data.index(0, i); out[key] = data[i:end].decode('utf-8'); i = end + 1
        elif kind == INT:
            out[key] = struct.unpack_from('<I', data, i)[0]; i += 4
        else:
            raise ValueError(f'unknown VDF type {kind} at {i}')


def dump(node):
    out = bytearray()
    for key, value in node.items():
        k = key.encode('utf-8') + b'\0'
        if isinstance(value, dict):
            out += bytes([MAP]) + k + dump(value)
        elif isinstance(value, int):
            out += bytes([INT]) + k + struct.pack('<I', value)
        else:
            out += bytes([STR]) + k + value.encode('utf-8') + b'\0'
    return bytes(out) + bytes([END])


def appid(exe, name):
    # Steam's id for a non-Steam shortcut: CRC32 of exe + name with the top bit set.
    return binascii.crc32((exe + name).encode('utf-8')) | 0x80000000


def backup(path, slug):
    # Keep the first backup: a re-run must not overwrite the pristine copy.
    if not os.path.exists(f'{path}.before-{slug}'):
        shutil.copy2(path, f'{path}.before-{slug}')


def set_compat_tool(app, tool, slug):
    path = f'{STEAM}/config/config.vdf'
    text = open(path, encoding='utf-8').read()
    m = re.search(r'\n(\t*)"CompatToolMapping"\n\t*\{\n', text)
    if not m:
        sys.exit('CompatToolMapping not found in config.vdf')
    # Drop an existing mapping for this appid, then insert ours at the top of the block.
    ind = m.group(1) + '\t'
    text = re.sub(rf'\n{ind}"{app}"\n{ind}\{{\n.*?\n{ind}\}}', '', text, flags=re.S)
    m = re.search(r'\n(\t*)"CompatToolMapping"\n\t*\{\n', text)
    block = (f'{ind}"{app}"\n{ind}{{\n{ind}\t"name"\t\t"{tool}"\n{ind}\t"config"\t\t""\n'
             f'{ind}\t"priority"\t\t"250"\n{ind}}}\n')
    backup(path, slug)
    open(path, 'w', encoding='utf-8').write(text[:m.end()] + block + text[m.end():])


def main():
    name, exe_path, start, opts = sys.argv[1:5]
    tool = sys.argv[5] if len(sys.argv) > 5 else 'proton_experimental'
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    exe = f'"{exe_path}"'
    app = appid(exe, name)
    for path in glob.glob(f'{STEAM}/userdata/*/config/shortcuts.vdf'):
        root, _ = parse(open(path, 'rb').read())
        shortcuts = root.get('shortcuts', {})
        template = next(iter(shortcuts.values()), {})
        kept = [s for s in shortcuts.values() if s.get('AppName', s.get('appname')) != name]
        entry = {'appid': app, 'appname': name, 'exe': exe, 'StartDir': f'"{start.rstrip("/")}/"',
                 'icon': '', 'ShortcutPath': '', 'LaunchOptions': opts, 'IsHidden': 0,
                 'AllowDesktopConfig': 1, 'AllowOverlay': 1, 'OpenVR': 0, 'Devkit': 0,
                 'DevkitGameID': '', 'DevkitOverrideAppID': 0, 'LastPlayTime': 0,
                 'FlatpakAppID': '', 'sortas': '', 'tags': {}}
        # Keep any extra fields this Steam version writes, with neutral values.
        for key, value in template.items():
            if key.lower() not in {k.lower() for k in entry}:
                entry[key] = {} if isinstance(value, dict) else 0 if isinstance(value, int) else ''
        kept.append(entry)
        backup(path, slug)
        root['shortcuts'] = {str(i): s for i, s in enumerate(kept)}
        open(path, 'wb').write(dump(root))
        print(f'{path}: {len(kept)} shortcuts')
    set_compat_tool(app, tool, slug)
    print(f'{name}: appid {app}, rungameid {(app << 32) | 0x02000000}, compat tool {tool}')


if __name__ == '__main__':
    main()
