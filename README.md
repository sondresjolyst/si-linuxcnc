# si-linuxcnc

LinuxCNC 2.9 configuration for a PrintNC router on a Raspberry Pi.

## Machine

| | |
| --- | --- |
| Kinematics | `XYYZ` trivkins, gantry on two Y joints |
| Travel | X 600 mm, Y 400 mm, Z 160 mm |
| Rapids | 29 mm/s, 100 mm/s² |
| Control | Raspberry Pi, step/dir and switches on the GPIO header |
| Spindle | 2.2 kW water cooled, 24000 rpm, Huanyang VFD over RS-485 |
| Probe | fixed tool setter, normally closed probe and over-travel contacts |

## What the config adds

| | |
| --- | --- |
| Tool setter | Z zero restored after a tool change from one calibration per setup, so stickout is never measured |
| Touch off buttons | X, Y and Z zero from the panel, each gated by an OK/Cancel dialog naming the axis |
| Spindle readout | speed in rpm, output current and VFD link status, read back over RS-485 |
| Run time estimate | percentage, minutes elapsed and minutes left for the running program |

## Installation

LinuxCNC reads configs and G-code from `~/linuxcnc`:

```console
git clone git@github.com:sondresjolyst/si-linuxcnc.git ~/linuxcnc
linuxcnc ~/linuxcnc/configs/printnc-axis/cncRouter.ini
```

## Setting up a job

Home the machine, then, from the panel beside the tool path:

1. Jog to the work origin, press **Touch off X**, **Touch off Y** and
   **Touch off Z**.
2. Press **Calibrate setter**, tool still clamped. This measures the height of
   the setter trigger point above the workpiece top.
3. After each tool change, press **Touch new tool**.

Step 3 restores Z. X and Y survive a tool change. Step 2 repeats when the
workpiece or the setter moves.

## Documentation

| | |
| --- | --- |
| [configs/README.md](configs/README.md) | running the config, the panel, the HAL pins behind it |
| [nc_files/macros/README.md](nc_files/macros/README.md) | tool setter macros, `[TOOLSENSOR]` keys, sensor wiring, commissioning |

## License

[MIT](LICENSE).
