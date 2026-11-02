#!/usr/bin/env bash
# Die Hard: Nakatomi Plaza (2002, v1.04) on the Steam Deck.
#
# Fixes the game under Proton and adds it to Steam:
#   1. startup hang (100% CPU, RAM climbs, no window)   -> patch cshell.dll inside Nakatomi3.rez
#   2. black screen after the fix above (input loop)    -> patch lithtech.exe
#   3. characters are floating heads                    -> DXVK for Direct3D 8 (PROTON_DXVK_D3D8=1)
#   4. no controls in game                              -> write the game's default key/mouse bindings
#   5. 4:3 in game                                      -> 1280x800 (16:10) in autoexec.cfg
#   6. Steam entry running lithtech.exe under Proton Experimental (no CD needed)
#
# Usage (Desktop Mode, in Konsole):
#   ./install.sh [options] GAME_FOLDER
#
#   GAME_FOLDER        where the game is (or will be) installed, e.g. ~/Games/Die\ Hard\ Nakatomi\ Plaza
#   --disc DIR         install from your own game disc (mounted disc/ISO with setup.exe) into GAME_FOLDER
#   --patch DIR        folder with the official v1.04 patch files (lithtech.exe, Nakatomi3.rez, SoundMAX.dll)
#   --name NAME        Steam shortcut name (default "Die Hard: Nakatomi Plaza")
#   --no-shortcut      only patch and configure, don't touch Steam
#   --resolution WxH   in-game resolution (default 1280x800)
#
# Everything it changes is backed up next to the original (*.orig, *.before-deck, *.before-<name>).
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
STEAM_DIR="$HOME/.local/share/Steam"
PROTON="$STEAM_DIR/steamapps/common/Proton - Experimental/proton"
NAME="Die Hard: Nakatomi Plaza"
DISC="" PATCH="" SHORTCUT=1 RES="1280x800" GAME=""

die() { echo "ERROR: $*" >&2; exit 1; }
step() { echo; echo "==> $*"; }

while [[ $# -gt 0 ]]; do
    case $1 in
        --disc) DISC=$2; shift 2 ;;
        --patch) PATCH=$2; shift 2 ;;
        --name) NAME=$2; shift 2 ;;
        --no-shortcut) SHORTCUT=0; shift ;;
        --resolution) RES=$2; shift 2 ;;
        -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) die "unknown option $1 (see --help)" ;;
        *) GAME=$1; shift ;;
    esac
done
[[ -n $GAME ]] || die "give the game folder (see --help)"
[[ $RES =~ ^[0-9]+x[0-9]+$ ]] || die "--resolution must look like 1280x800"
command -v python3 >/dev/null || die "python3 not found"
mkdir -p "$GAME"
GAME=$(cd "$GAME" && pwd)

# Find a file case-insensitively in a folder (the game's files mix upper and lower case).
find_ci() { find "$1" -maxdepth 1 -iname "$2" -print -quit; }

if [[ -n $DISC ]]; then
    step "Installing from disc: $DISC"
    setup=$(find_ci "$DISC" setup.exe); [[ -n $setup ]] || die "no setup.exe in $DISC"
    [[ -x $PROTON ]] || die "Proton Experimental not installed (install it from Steam > Library > Tools)"
    pfx=$(mktemp -d "${TMPDIR:-/tmp}/dhnp-install.XXXXXX")
    export STEAM_COMPAT_DATA_PATH=$pfx STEAM_COMPAT_CLIENT_INSTALL_PATH=$STEAM_DIR
    # Silent Wise install. It also starts a DirectX 8 setup that never finishes; Proton already
    # provides Direct3D, so close it once the game files are in place.
    # "./" matters: a bare setup.exe makes Wine look it up somewhere else and nothing happens.
    (cd "$(dirname "$setup")" && "$PROTON" run "./$(basename "$setup")" /s >/dev/null 2>&1) &
    src="$pfx/pfx/drive_c/Program Files (x86)/Fox/Die Hard Nakatomi Plaza"
    # Done when INSTALL.LOG exists and the file count has stopped changing for 10 s.
    last=-1 same=0
    for _ in $(seq 1 600); do
        n=$(find "$src" -type f 2>/dev/null | wc -l || true)
        if [[ -f $src/INSTALL.LOG && $n == "$last" ]]; then same=$((same + 1)); else same=0; fi
        [[ $same -ge 10 ]] && break
        last=$n; sleep 1
    done
    [[ -f $src/Nakatomi.rez ]] || die "the installer didn't produce the game files (see $pfx)"
    sleep 3
    for p in $(pgrep -x dx80nt.exe) $(pgrep -x DXSETUP.exe); do kill "$p" 2>/dev/null || true; done
    WINEPREFIX="$pfx/pfx" "$(dirname "$PROTON")/files/bin/wineserver" -k 2>/dev/null || true
    cp -a "$src/." "$GAME/"
    rez2=$(find_ci "$DISC" nakatomi2.rez); [[ -n $rez2 ]] || die "no nakatomi2.rez on the disc"
    cp "$rez2" "$GAME/Nakatomi2.rez"; chmod u+w "$GAME/Nakatomi2.rez"
    rm -rf "$pfx"
fi

if [[ -n $PATCH ]]; then
    step "Applying the v1.04 patch from $PATCH"
    for f in lithtech.exe Nakatomi3.rez SoundMAX.dll; do
        p=$(find_ci "$PATCH" "$f"); [[ -n $p ]] || die "$f missing from $PATCH"
        old=$(find_ci "$GAME" "$f"); [[ -n $old && ! -e $old.v100 ]] && cp -p "$old" "$old.v100"
        [[ -n $old && $(basename "$old") != "$f" ]] && rm -f "$old"   # e.g. Lithtech.exe -> lithtech.exe
        cp "$p" "$GAME/$f"
    done
fi

step "Checking the game folder"
for f in lithtech.exe Engine.rez Nakatomi.rez Nakatomi3.rez; do
    [[ -n $(find_ci "$GAME" "$f") ]] || die "$f not found in $GAME (install the game and the v1.04 patch first)"
done
if [[ -z $(find_ci "$GAME" nakatomi2.rez) ]]; then
    die "Nakatomi2.rez not found. It stays on the disc: copy nakatomi2.rez from the disc's root into $GAME"
fi
# lithtech.exe must be the 1.04 one, named in lower case for the launch command.
lt=$(find_ci "$GAME" lithtech.exe); [[ $(basename "$lt") == lithtech.exe ]] || mv "$lt" "$GAME/lithtech.exe"
rez3=$(find_ci "$GAME" nakatomi3.rez)

step "Fixing the startup hang (cshell.dll in Nakatomi3.rez)"
python3 "$HERE/tools/patch_cshell.py" "$rez3"
step "Fixing the input loop that leaves the screen black (lithtech.exe)"
python3 "$HERE/tools/patch_lithtech.py" "$GAME/lithtech.exe"
step "Setting ${RES} and the default controls"
python3 "$HERE/tools/make_config.py" "$GAME" "${RES%x*}" "${RES#*x}"

if [[ $SHORTCUT == 1 ]]; then
    step "Adding \"$NAME\" to Steam"
    if pgrep -f start-gamescope-sessio[n] >/dev/null; then
        die "you're in Gaming Mode. Switch to Desktop Mode and run this again (Steam must be closed to add a shortcut)"
    fi
    restart=0
    if pgrep -x steam >/dev/null; then
        echo "Closing Steam (it rewrites its shortcut list when it exits)..."
        restart=1
        pkill -TERM -x steam || true
        for _ in $(seq 1 90); do pgrep -x steam >/dev/null || break; sleep 1; done
        pgrep -x steam >/dev/null && die "Steam didn't close; quit it yourself and run this again"
        sleep 2
    fi
    opts="PROTON_DXVK_D3D8=1 %command% -rez engine.rez -rez nakatomi.rez -rez nakatomi2.rez -rez nakatomi3.rez"
    python3 "$HERE/tools/add_proton_shortcut.py" "$NAME" "$GAME/lithtech.exe" "$GAME" "$opts" proton_experimental
    if [[ $restart == 1 ]]; then
        echo "Starting Steam again..."
        if [[ -n ${DISPLAY:-} ]]; then setsid -f steam >/dev/null 2>&1
        else systemd-run --user --collect env DISPLAY=:0 steam -silent >/dev/null 2>&1; fi
    fi
fi

cat <<EOF

Done. In Steam, open "$NAME" > Controller settings and pick the
"Keyboard (WASD) and Mouse" layout: left stick moves, right stick/trackpad looks,
right trigger fires, A jumps, X reloads, Y uses, Menu opens the game menu.
The menus are always 4:3 in this game; gameplay is $RES.
EOF
