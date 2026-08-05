# Tool setter macros

A fixed tool setter standing at one spot on the table. Tools are clamped by
hand in an ER20 collet, so stickout differs every time and the tool table
cannot describe it. Instead the setter measures one number per *setup*:

    D = height of the setter trigger point above the workpiece top

D does not depend on the tool, because zeroing Z on the part and triggering the
setter both move by the same amount when stickout changes. Measure D once with
a known-good Z zero, and every later tool is zeroed by probing the setter and
declaring the trigger point to be D.

    o<setter_cal> call     once per setup, while Z zero is still good
    o<setter_zero> call    after every tool change

`setter_probe.ngc` holds the motion both share. D lives in the G59.3 origin
(`#5383`, valid flag `#5381`) because those parameters are already persistent
in `linuxcnc.var`. **G59.3 must not be used as a work coordinate system** —
selecting it would move the machine by D.

Position, travel and speeds come from `[TOOLSENSOR]` in
`configs/printnc-axis/cncRouter.ini`.

## Still open

- `[TOOLSENSOR]` `X`, `Y`, `SAFE_Z`, `MAXPROBE` are placeholders. Step 4
  settles them.

## At the machine

Working through this in order.

### 1. What the setter actually is

Metered on the bench, disconnected, nothing powered:

| Measurement | Plunger free | Plunger pressed |
|---|---|---|
| red ↔ black | closed, 0.8 ohm | opens on slight touch |
| green ↔ yellow | closed, 0.8 ohm | opens at bottom of travel |
| red ↔ green, red ↔ yellow, black ↔ green, black ↔ yellow | open | open |
| any wire ↔ housing | open | open |

0.8 ohm reads the same in both meter directions, and the state changes with no
supply connected, which only a mechanical contact does. So: two isolated
normally-closed switches, red+black triggering on contact and green+yellow at
the end of plunger travel. Nothing needs 24 V and the PNP/NPN question in the
seller's sheet does not apply.

The seller's sheet says something different — green as the tool approach
output, red and black both as supply, 24 V, PNP or NPN. It predicts red↔black
closed in every plunger position and green↔yellow never closed, and the meter
says the opposite of both. Treated as a generic listing blurb, not as this
unit. Meter again if the setter is ever replaced.

Normally closed is the safe polarity either way: a cut wire or a pulled
connector looks the same as triggered, so LinuxCNC refuses to start a probe
instead of driving a tool through the setter.

### 2. Wire it, machine powered down

The rule, whatever the colours turn out to be on a given unit: **the pair that
opens on slight touch is the probe.** Measured here, that is red+black.

Wired like the limit switches already on this machine — a contact between an
input terminal and the shared input common. Dry contacts are not polarised, so
within a pair either wire can take either end.

| Wire | Goes to |
|---|---|
| red | breakout board terminal `P11`, which reaches header pin 24 |
| black | input GND/COM, the terminal the limit switch returns land on |
| green | breakout board terminal `P10`, header pin 22, in place of the ground strap that was there |
| yellow | input GND/COM, same terminal as black |

Don't reason about whether that common is 0 V or +V. Whatever makes a limit
switch work makes this work.

The over-travel pair lands on Z's negative limit, `joint.3.neg-lim-sw-in`, which
had nothing on it. Bottoming the plunger faults the machine; Override Limits
jogs Z back off it.

The contactor chain runs at 230 V, so the pair stays out of it. To move it into
hardware later, put green and yellow on the coil of a 24 V interface relay and
break the chain with that relay's NO contact. The setter cable doesn't change.

### 3. Check the input in LinuxCNC

Power up, start LinuxCNC, press the plunger by hand and watch the probe LED on
the pyvcp panel.

- Green when pressed, red when released: correct, move on.
- Backwards: swap `PIN24-in` for `PIN24-in-not` in `configs/common/cncRouter.hal`.
- No reaction: the probe wire is not on `P11`. Trace the terminal with
  LinuxCNC closed, which reads pins without driving anything:

      cat > /tmp/probetrace.hal <<'EOF'
      loadrt hal_gpio inputs=PIN3,PIN5,PIN7,PIN8,PIN10,PIN15,PIN22,PIN24,PIN26,PIN32,PIN33,PIN36,PIN38,PIN40
      loadrt threads name1=t1 period1=1000000
      addf hal_gpio.read t1
      start
      EOF
      halrun -I -f /tmp/probetrace.hal

  Run `show pin hal_gpio` at the `halcmd:` prompt, press the plunger, run it
  again and see which pin flipped. Press a limit switch first as a control —
  `PIN26`, `PIN32` and `PIN33` are the limit inputs already in use, and if none
  of them move either then the fault is board power, not the terminal. Put the
  pin that responds into the `net probe-input` line, and add it to `inputs=` on
  the `loadrt hal_gpio` line if it is not listed. Don't use `sudo`: halrun
  refuses to run as root.

Then the over-travel pair: with the machine on, push the plunger all the way to
its stop. LinuxCNC must fault on a Z negative limit. Unplug the setter and it
must do the same. Clear it with Override Limits.

Do not go further until the LED follows the plunger. Everything below drives
the spindle at the setter.

### 4. Measure the setter position

Home the machine. Jog the tool over the setter centre, then read the machine
coordinates — in AXIS switch the DRO to machine coordinates, or run
`(debug, #<_abs_x> #<_abs_y> #<_abs_z>)` in MDI.

Fill into `[TOOLSENSOR]`:

- `X`, `Y` — setter centre, machine coordinates.
- `SAFE_Z` — machine Z the tool travels at when crossing the table to the
  setter. High enough to clear the workpiece and clamps, at or below 0.
- `MAXPROBE` — how far down from `SAFE_Z` the probe may search. Enough to
  reach the setter with your shortest tool, not so much that a missed trigger
  runs the spindle into the table.

### 5. Dry-run the probe

Machine homed, **no tool in the collet**, spindle off. Hold the setter plunger
down by hand and run:

    o<setter_probe> call

It must abort immediately with a probe-already-tripped error. That proves
LinuxCNC is reading the sensor.

Release it and run again. The collet nut should travel to the setter and stop
on contact. Hand on the e-stop for this one — a wrong `X`/`Y` sends it
somewhere else, and a wrong polarity means it does not stop at all.

### 6. Calibrate

With a tool clamped and Z zeroed on the workpiece top the way you normally do
it:

    o<setter_cal> call

The status line reports D. Sanity-check the sign: positive when the setter
trigger point sits above the workpiece top, negative when the workpiece is
taller than the setter.

### 7. Confirm D survives a restart

Once, on the LinuxCNC version you actually run:

    o<setter_cal> call
    (debug, #5383)

Quit LinuxCNC, check the number appears in `configs/printnc-axis/linuxcnc.var`
on line `5383`, restart, and run `(debug, #5383)` again. Same value means the
storage works. Repeat this check after a LinuxCNC upgrade.

### 8. Use it

Tool change: stop, swap the tool, then press **Zero Z from setter** on the
pyvcp panel, or run

    o<setter_zero> call

Z zero is restored. The panel's probe LED follows `motion.probe-input` — green
means triggered, so it should be red with the plunger released. Calibration has
no button on purpose: it is a once-per-setup command, and a stray click on it
after a tool change would store a wrong D. X and Y are untouched, so they survive a tool change on
their own.

Recalibrate with `setter_cal` whenever the workpiece or the setter moves. The
macro cannot detect a stale D — it will happily zero against the previous
setup's number.
