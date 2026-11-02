# Die Hard: Nakatomi Plaza on the Steam Deck

A script that gets the 2002 PC game **Die Hard: Nakatomi Plaza** (v1.04) running properly on the Steam Deck under Proton, and adds it to Steam:

| Problem under Proton | Fix |
|---|---|
| Game never starts: one CPU core at 100%, RAM climbing, no window | Patch to `cshell.dll` (inside `Nakatomi3.rez`) |
| After that, a black screen forever | Patch to the input loop in `lithtech.exe` |
| Characters are floating heads | DXVK for Direct3D 8 (`PROTON_DXVK_D3D8=1`) |
| Nothing you press does anything in game | Writes the game's default key/mouse bindings |
| 4:3 picture | Sets 1280x800 (16:10) |
| Needs the CD | Steam starts `lithtech.exe` directly, so no disc check and no crack needed |

You need **your own copy of the game**. This repo contains no game files.

## What you need

- The game's files from your own disc, either as a disc or a disc image you can mount, or as an installed copy from a Windows PC.
- The official **v1.04 patch** files: `lithtech.exe`, `Nakatomi3.rez`, `SoundMAX.dll`. If your patch came as an installer, install it on a Windows PC or in Proton first, and point the script at your patched folder instead.
- **Proton Experimental**, which you can install from Steam > Library > Tools.

## Install

On the Deck, switch to **Desktop Mode** and open **Konsole**:

```bash
git clone https://github.com/wiggyoats/die-hard-nakatomi-plaza-steam-deck
cd die-hard-nakatomi-plaza-steam-deck
```

Then pick one of these:

**From the disc** (mounted disc or ISO with `setup.exe` on it):

```bash
./install.sh --disc /run/media/deck/NAKATOMI --patch ~/Downloads/v104-patch ~/Games/"Die Hard Nakatomi Plaza"
```

**From a copy you've already installed** (with v1.04 applied, and `nakatomi2.rez` copied from the disc's root into the game folder):

```bash
./install.sh ~/Games/"Die Hard Nakatomi Plaza"
```

The script will:

1. install from the disc silently, if you used `--disc`
2. apply the v1.04 patch, if you used `--patch`
3. patch the two bugs
4. set 1280x800 and the controls
5. close Steam, add a **"Die Hard: Nakatomi Plaza"** entry that runs under Proton Experimental with DXVK, and start Steam again

Every file it changes is backed up next to the original (`*.orig`, `*.v100`, `*.before-deck`).

Then go back to Gaming Mode, open the game's **Controller settings** and pick **Keyboard (WASD) and Mouse**:

| Deck | Game |
|---|---|
| Left stick (click) | Move (run) |
| Right stick / right trackpad | Look |
| Right trigger / left trigger | Fire / alt-fire |
| A / X / Y / B | Jump / reload / use / lean right |
| D-pad | Look up/down, turn |
| Menu | Game menu |

Crouch is Ctrl, which that layout doesn't map, so add it to a spare button if you want it. The mouse is very sensitive by default; turn it down in Options > Controls.

Options: `--name "Other name"` for the Steam entry, `--resolution 1280x720`, and `--no-shortcut` to patch only, for example on a desktop Linux PC.

## Notes

- The menus are always 640x480 (4:3) in this game. Gameplay and cutscenes are 16:10.
- The intro movies play; press Esc to skip them.
- Exit through the in-game menu (Esc > Exit) so the game saves your settings.

## What the patches do

Both patches are a handful of bytes. The scripts check the exact original bytes before changing anything, refuse to touch other versions, and can safely be run twice.

**`tools/patch_cshell.py`:** the game's mission-list object (0x12a4 bytes, allocated with `new`) never zeroes its mission counters, and the main menu reads them before the loader fills them in. On Windows that memory happens to be zero. Under Wine it's recycled heap memory that can still hold text from the environment, so the menu tries to build about 1.6 billion entries. The patch redirects the object's constructor through a 20-byte stub, placed in unused space at the end of `.text`, that zero-fills the object first.

**`tools/patch_lithtech.py`:** each frame the engine reads buffered DirectInput data. For the mouse it reads one event at a time, and repeats for as long as a read returns anything. Wine's DirectInput keeps reporting one empty event for this mouse, so the loop never ends and no frame is ever drawn. The patch makes the mouse use the same path as every other device: read up to 64 events, once per frame.

**DXVK:** Wine's built-in Direct3D 8 (wined3d) doesn't draw the game's skinned character models. DXVK's Direct3D 8 does.

**Controls:** the installer never writes the default bindings into `autoexec.cfg`, so under Proton the game has none. `tools/default-binds.cfg` holds the game's own defaults.

## License

MIT for the scripts in this repo. Die Hard: Nakatomi Plaza belongs to its rights holders; this project isn't affiliated with them.
