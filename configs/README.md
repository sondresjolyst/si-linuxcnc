# PrintNC LinuxCNC configs

Three front ends for the same machine. Pick one in the LinuxCNC config picker,
or launch directly:

    linuxcnc configs/printnc-axis/cncRouter.ini
    linuxcnc configs/printnc-gmoccapy/cncRouter.ini
    linuxcnc configs/printnc-qtdragon/cncRouter.ini

| Config | GUI | Dark theme | Progress / time left |
|---|---|---|---|
| `printnc-axis` | AXIS | no, AXIS has no theming | no |
| `printnc-gmoccapy` | GMOCCAPY | yes, follows the GTK desktop theme | GMOCCAPY's own percent, plus the Progress tab |
| `printnc-qtdragon` | QtDragon | yes, ships dark stylesheets | Progress tab |

`printnc-axis` is the original config, untouched, and stays the known-good
fallback. QtDragon needs a screen of at least 1280x768; below that use
GMOCCAPY.

## What is shared

`common/` holds everything that is not GUI specific, and each config links to
it, so a change to the machine wiring reaches all three:

- `common/cncRouter.hal` — the machine HAL. Symlinked as `cncRouter.hal` in
  every config directory.
- `common/progress.py` — HAL component publishing progress and the time
  estimate.
- `common/progress.hal` — loads that component and wires it to the panel.
  Symlinked into the two new configs.
- `common/eta.ui` — the GladeVCP panel that displays it.

Per-config files stay local: `cncRouter.ini`, `custom.hal`,
`custom_postgui.hal`, `tool.tbl`, `linuxcnc.var`.

Because the shared files are symlinks, copying a single config directory out of
this repo breaks it. Copy `common/` alongside it, or replace the symlinks with
real files.

## Progress and estimated time left

Neither GUI can estimate run time on its own, so `common/progress.py` does it.
It watches the LinuxCNC status channel and exports:

    progress.percent       0-100, share of the file executed
    progress.elapsed-min   minutes running, paused time excluded
    progress.remain-min    estimated minutes left
    progress.total-min     estimated minutes for the whole program
    progress.line          line being executed
    progress.lines         lines in the loaded file
    progress.running       1 while a program is running

The estimate extrapolates from the run so far: if 25% of the file has executed
in 5 minutes, the whole program is called 20 minutes. Progress is counted in
lines, not in distance or time, so a file whose slow cuts sit at the end will
read optimistic, and one that starts with a long roughing pass will read
pessimistic. It settles down as the run proceeds. Nothing is published until
2% of the file has run, because the first few lines produce nonsense.

The values are visible without any GUI support at all — `halshow`, or
`halmeter pin progress.remain-min`.

## Turning on the dark theme

**GMOCCAPY** uses the GTK desktop theme. In the GUI go to the settings page,
Appearance, and pick a dark theme such as `Adwaita-dark`; the choice is saved in
`gmoccapy.pref`. If no dark theme is listed, install one on the Pi:

    sudo apt install gnome-themes-extra

To force it for one run without touching the settings:

    GTK_THEME=Adwaita-dark linuxcnc configs/printnc-gmoccapy/cncRouter.ini

**QtDragon** ships its own stylesheets. Press `F12` in the running GUI to open
the stylesheet editor and select the dark `.qss`; the choice is saved in
`qtdragon.pref`.

Both are runtime settings stored in the preference files, which is why they are
not committed here.

## If the QtDragon Progress tab stays empty

The tab embeds a GladeVCP panel. GMOCCAPY documents that form of embedding;
QtDragon's own examples embed qtvcp panels instead, so if it refuses to
reparent, comment out the three `EMBED_TAB_*` lines in
`printnc-qtdragon/cncRouter.ini` together with the `source progress.hal` line in
`printnc-qtdragon/postgui_call_list.hal`. The pins stay available in `halshow`.
