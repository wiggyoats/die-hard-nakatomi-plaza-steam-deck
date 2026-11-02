#!/usr/bin/env python3
"""Set up autoexec.cfg for the Steam Deck: 1280x800 at 32-bit and working keyboard/mouse bindings.

The installer never writes the game's default control bindings, so under Proton nothing you press
in-game does anything (menus still work). This replaces the binding lines with the game's own
defaults (default-binds.cfg, next to this script) and sets the Deck's native resolution.

Usage: make_config.py <game folder> [WIDTH HEIGHT]   (keeps autoexec.cfg.before-deck as a backup)
"""
import os
import re
import shutil
import sys

BIND_PREFIXES = ("enabledevice ", "rangebind ", "scale ", '"enabledevice" ')


def set_var(text, name, value):
    pattern = re.compile(rf'^"{name}" "[^"]*"$', re.M | re.I)
    line = f'"{name}" "{value}"'
    return pattern.sub(line, text) if pattern.search(text) else text.rstrip("\n") + "\n" + line + "\n"


def main():
    game = sys.argv[1]
    width, height = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ("1280", "800")
    cfg = os.path.join(game, "autoexec.cfg")
    binds = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "default-binds.cfg")).read()

    text = open(cfg, encoding="latin-1").read() if os.path.exists(cfg) else ""
    if text and not os.path.exists(cfg + ".before-deck"):
        shutil.copy2(cfg, cfg + ".before-deck")

    for name, value in (("screenwidth", width), ("screenheight", height), ("bitdepth", "32"),
                        ("32bittextures", "1")):
        text = set_var(text, name, value)
    kept = [l for l in text.splitlines() if not l.startswith(BIND_PREFIXES)]
    text = "\n".join(kept).rstrip("\n") + "\n\n" + binds
    with open(cfg, "w", encoding="latin-1", newline="\n") as f:
        f.write(text)
    print(f"autoexec.cfg: {width}x{height}x32, {binds.count('rangebind')} default bindings")


if __name__ == "__main__":
    main()
