# PrintNC LinuxCNC config

```console
linuxcnc configs/printnc-axis/cncRouter.ini
```

AXIS front end with a PyVCP panel beside the tool path. HAL that is not
front end specific lives in `common/` and is symlinked into the config.

## Panel

| Frame | Contents |
| --- | --- |
| Touch off | Touch off X, Y and Z, each releasing its MDI command only after an OK/Cancel dialog |
| Tool setter | probe LED, Calibrate setter, Touch new tool |
| Spindle | VFD link LED, speed in rpm, output current in amps |
| Progress | percentage bar, minutes left, minutes elapsed |

## Pins

Everything on the panel is a HAL pin, so it is also readable from `halshow`, or
from the command line:

```console
halmeter pin progress.remain-min
```

| Pin | Value |
| --- | --- |
| `progress.percent` | 0-100, share of the file executed |
| `progress.elapsed-min` | minutes running, paused time excluded |
| `progress.remain-min` | estimated minutes left |
| `progress.total-min` | estimated minutes for the whole program |
| `progress.line` | line being executed |
| `progress.lines` | lines in the loaded file |
| `progress.running` | 1 while a program is running |
| `vfd.spindle-speed-fb` | spindle speed reported by the VFD, rpm |
| `vfd.OutA` | VFD output current, amps |
| `vfd.hycomm-ok` | 1 while the RS-485 link is up |

## Run time estimate

`common/progress.py` extrapolates from the run so far and counts executed lines
rather than distance or time. A program whose slow cuts sit at the end reads
optimistic, one that opens with a long roughing pass reads pessimistic, and both
converge as the run proceeds. The estimate appears once 2% of the file has run.
