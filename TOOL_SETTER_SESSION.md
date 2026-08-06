# Tool setter install — where we left off

Branch `feat/tool-setter-probe`, all work committed and pushed. Machine needs
`cd ~/linuxcnc && git pull` to pick up `6f5658d`.

## Traced at the machine

| BOB terminal | RPi header pin | Use |
|---|---|---|
| `P11` | 24 | probe, red+black |
| `P10` | 22 | over-travel, green+yellow — replaced a ground strap |

Traced with `halrun`, LinuxCNC closed, no `sudo`:

    cat > /tmp/probetrace.hal <<'EOF'
    loadrt hal_gpio inputs=PIN3,PIN5,PIN7,PIN8,PIN10,PIN15,PIN22,PIN24,PIN26,PIN32,PIN33,PIN36,PIN38,PIN40
    loadrt threads name1=t1 period1=1000000
    addf hal_gpio.read t1
    start
    EOF
    halrun -I -f /tmp/probetrace.hal

`show pin hal_gpio` before and after pressing the switch.

Polarity: both pairs normally closed, so `-in` reads FALSE at rest and TRUE when
triggered or cut. `PIN24-in` drives `motion.probe-input`, `PIN22-in` drives
`joint.3.neg-lim-sw-in`.

## Decisions made

- Over-travel goes to Z's negative limit, not e-stop. Bottoming the plunger is
  the spindle standing on the setter, and e-stop would refuse to enable the
  machine that has to lift off it. Override Limits jogs out of a limit.
- It is not in the contactor chain: that runs at 230 V through an
  AF09-30-10-13. Hardware version later would be a 24 V interface relay, coil
  on green/yellow, NO contact breaking the chain. Setter cable unchanged.
- No probe bypass toggle. A tripped probe blocks a move only on a rising edge,
  so jogging off the setter works with the LED green — tested.
- The panel carries the whole touch-off: **Touch off X**, **Touch off Y**,
  **Touch off Z**, **Touch new tool**. X and Y are plain `G10 L20 P0 X0`/`Y0`
  through halui; Z runs `setter_touchoff_z`, which zeroes Z and then calls
  `setter_cal`, so a setup is one press per axis with no separate calibrate
  step. AXIS's Touch Off is still there for offsets that need typing.
  Rejected: a standalone **Calibrate setter** button next to AXIS Touch Off
  (three presses to start a job), and `o<setter_cal> call` in the
  post-processor preamble (one post out of sync and it silently goes missing).

## `[TOOLSENSOR]`

Setter sits under the home position, so X and Y are 0. Trigger at machine
Z -52.06 with a 75 mm tool at 55 mm stickout, which puts the collet nut at the
setter around -107. `MAXPROBE = 88` from `SAFE_Z = -5` reaches -93.

## Done

1. Metered the setter — two isolated NC switches.
2. Wired red+black to `P11`, green+yellow to `P10`.
3. Input verified. Probe aborts with `Probe is already tripped when starting
   G38.2 or G38.3 move` on a light press; a full press faults joint 3.
4. `[TOOLSENSOR]` filled.
5. Dry run passed both halves, no errors.

## Next

6. Calibrate. Tool clamped, jog Z to the workpiece top, press **Touch off Z**.
   It zeroes Z and drives to the setter. Check the sign of D — positive when
   the trigger point is above the workpiece top.
7. Confirm D survives a restart: `(debug, #5383)`, quit, check line `5383` of
   `configs/printnc-axis/linuxcnc.var`, restart, `(debug, #5383)` again.
8. Then it's in use.

## Untested

The retract at the end of `setter_cal`/`setter_zero` starts from a tripped
probe. `setter_probe` alone was fine, so it should be, but step 6 is the first
time that path runs.

## Known, not touched

`configs/common/cncRouter.hal` nets `all-limit => joint.2` twice — the block
under Z's stepgen is a copy of the Y1 block. `all-limit` has no writer either,
so Z has no limit switch inputs beyond the setter's. Left alone deliberately.
