# Fixed tool setter

Restores Z zero after a tool change on a machine with hand-clamped ER20
collets, where stickout varies with every tool and the tool table cannot
describe it.

## How it works

The setter measures one value per setup:

    D = height of the setter trigger point above the workpiece top

D is independent of the tool: changing stickout shifts the workpiece touch-off
point and the setter trigger point by the same amount. Once D is known, any
tool is zeroed by probing the setter and declaring the trigger point to be D.

D is held in the G59.3 origin (`#5383`), with `#5381` as a validity flag, since
those parameters persist in `linuxcnc.var` across restarts.

> G59.3 must not be selected as a work coordinate system. Doing so applies D as
> a work offset and moves the machine.

## Panel

`setter.xml` adds two pyvcp panels, **Touch off** and **Tool setter**. Tool
setter also carries an LED following `motion.probe-input`.

| Panel | Button | Macro | Effect |
|---|---|---|---|
| Touch off | Touch off X | — | Sets X zero at the current position |
| Touch off | Touch off Y | — | Sets Y zero at the current position |
| Touch off | Touch off Z | `setter_touchoff_z` | Sets Z zero at the current position and invalidates D |
| Tool setter | Calibrate setter | `setter_cal` | Traverses to the setter, probes it, stores D |
| Tool setter | Touch new tool | `setter_zero` | Traverses to the setter, probes it, restores Z zero from D |

A setup runs: touch off X, Y and Z, then **Calibrate setter** with that same
tool still clamped. Every tool change afterwards needs only **Touch new tool** —
X and Y are unaffected by a tool change.

Recalibrate whenever the workpiece or the setter moves. The AXIS Touch Off
dialog remains available for offsets that must be typed.

## Macros

| Macro | Effect |
|---|---|
| `setter_touchoff_z` | Sets Z zero at the current position and clears `#5381` |
| `setter_cal` | Probes the setter and stores D against the current Z zero |
| `setter_zero` | Probes the setter and restores Z zero from D |
| `setter_probe` | Two-pass probing move used by the above |

`setter_zero` aborts if `#5381` is not 1. Since a new Z zero puts the workpiece
top at a different height and makes D stale, `setter_touchoff_z` clears the
flag, so a calibration is required before the next tool change.

The machine must be homed: the approach to the setter is issued in G53.

## Configuration

`[TOOLSENSOR]` in `configs/printnc-axis/cncRouter.ini`:

| Key | Meaning |
|---|---|
| `X`, `Y` | Setter centre, machine coordinates |
| `SAFE_Z` | Machine Z for traverse to the setter; clears workpiece and clamps |
| `MAXPROBE` | Maximum probing depth below `SAFE_Z` |
| `SEARCH_VEL` | First-pass probing feed rate |
| `PROBE_VEL` | Second-pass probing feed rate |

To size `MAXPROBE`, measure the machine Z at which a tool of known length
triggers the setter. That fixes the trigger height, from which the depth
reached by the shortest tool and the depth at which the collet nut would meet
the setter body both follow. Choose a value that reaches the first and stops
short of the second.

Buttons are bound to `halui.mdi-command-NN` in `custom_postgui.hal`, where NN is
the position of the corresponding `MDI_COMMAND` entry under `[HALUI]`.
Reordering one requires reordering the other.

The three touch off buttons are routed through `setter_confirm.py`, a userspace
component started from `custom_postgui.hal`. It presents an OK/Cancel dialog
naming the axis and releases the command only on OK, so pressing the wrong one
of three adjacent buttons is caught before a zero is overwritten. To guard
another button, add its pin pair to `BUTTONS` and net it through the component
the same way.

## Wiring

Two isolated normally-closed contacts, both switched against the shared input
common, wired as the machine's limit switches are:

| Contact | Terminal | HAL |
|---|---|---|
| probe, opens on light contact | `P11`, header pin 24 | `motion.probe-input` |
| over-travel, opens at end of plunger travel | `P10`, header pin 22 | `joint.3.neg-lim-sw-in` |

Both pins must appear in the `inputs=` list of the `loadrt hal_gpio` line in
`configs/common/cncRouter.hal`. Dry contacts are not polarised, so either
conductor of a pair may take either end.

Normally closed is fail-safe: a severed conductor reads as triggered, so a
probing move is refused rather than begun. Bottoming the plunger faults the
machine on a Z negative limit, which Override Limits clears so the spindle can
be jogged clear of the setter.

### Using a different sensor

Meter the unit on the bench, disconnected and unpowered. A mechanical contact
reads the same resistance in both meter polarities and changes state with no
supply connected. If it behaves that way, no supply is needed and the PNP/NPN
distinction in the datasheet does not apply.

Identify the pairs by behaviour rather than by colour: **the contact that opens
on slight touch is the probe**, and the one that opens at the end of plunger
travel is the over-travel. Datasheets for these units are frequently generic
and may contradict the meter; trust the meter.

### Finding which header pin a terminal reaches

Breakout board labels bear no relation to Raspberry Pi header numbers. To trace
one, close LinuxCNC and read the pins without driving outputs:

    cat > /tmp/probetrace.hal <<'EOF'
    loadrt hal_gpio inputs=PIN3,PIN5,PIN7,PIN8,PIN10,PIN15,PIN22,PIN24,PIN26,PIN32,PIN33,PIN36,PIN38,PIN40
    loadrt threads name1=t1 period1=1000000
    addf hal_gpio.read t1
    start
    EOF
    halrun -I -f /tmp/probetrace.hal

Run `show pin hal_gpio` at the `halcmd:` prompt, operate the switch, and run it
again to see which pin changed. Trigger a known-good limit switch first as a
control; if nothing responds to that either, the fault is board power rather
than the terminal. Note that `halrun` refuses to run as root, and that pin
names take no leading zero — `PIN3`, not `PIN03`.

### Putting the over-travel into the power chain

The over-travel contact faults LinuxCNC but does not open the machine's power
chain. To break the chain in hardware as well, drive the coil of an interface
relay from the over-travel pair and wire that relay's NO contact into the
chain. This keeps the sensor cable, which is handled by hand, out of the chain
regardless of what the chain switches.

## Commissioning

Verify the input before running anything that drives the spindle towards the
setter.

1. Press the plunger by hand and watch the panel LED: green on light contact,
   red on release. If it is inverted, substitute `hal_gpio.PIN24-in-not` for
   `hal_gpio.PIN24-in`. If it does not respond at all, trace the terminal.
2. Push the plunger to its stop, and separately unplug the sensor. Both must
   fault the machine on a Z negative limit. Clear with Override Limits.
3. Home the machine, jog over the setter centre and record machine coordinates
   — switch the AXIS DRO to machine coordinates, or run
   `(debug, #<_abs_x> #<_abs_y> #<_abs_z>)` in MDI. Enter them in
   `[TOOLSENSOR]`.
4. Hold the plunger down lightly, enough for the LED to go green without
   bottoming it, and run `o<setter_probe> call`. The macro traverses to
   `SAFE_Z` and to X/Y, then aborts with `Probe is already tripped when
   starting G38.2 or G38.3 move`, confirming the input reaches the motion
   controller.
5. Release the plunger and repeat. The tool must travel to the setter and stop
   on contact. Keep a hand on the e-stop: an incorrect `X`/`Y` sends the tool
   elsewhere, and an inverted polarity means it does not stop. Use a tool of
   known trigger height rather than a bare collet, which may not reach within
   `MAXPROBE`.
6. Jog Z to the workpiece top, press **Touch off Z**, then **Calibrate
   setter**. D is reported on the status line; it is positive when the setter
   trigger point sits above the workpiece top.
7. Confirm D survives a restart: run `(debug, #5383)`, quit LinuxCNC, check the
   value on line `5383` of `configs/printnc-axis/linuxcnc.var`, restart and run
   `(debug, #5383)` again. Worth repeating after a LinuxCNC upgrade.
