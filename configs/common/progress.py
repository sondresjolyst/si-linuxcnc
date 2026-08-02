#!/usr/bin/env python3
"""HAL component reporting progress and a time estimate for the running program.

LinuxCNC has no notion of how long a program will take, so the estimate is
extrapolated from how long the run has taken so far: the fraction of the file
already executed is assumed to represent the same fraction of the total time.
That is accurate for a program with an even distribution of work and optimistic
for one that ends with the slow cuts, so treat it as a guide, not a promise.

Progress is measured in executed lines, taken from motion.line (the line the
machine is actually moving on) rather than the interpreter line, which runs
ahead of the motion by the look-ahead queue.

Pins, all float outputs so they drop straight into PyVCP number and GladeVCP
HAL_Label widgets:

    progress.percent      0-100, fraction of the file executed
    progress.elapsed-min  minutes spent running, paused time excluded
    progress.remain-min   estimated minutes left
    progress.total-min    estimated minutes for the whole program
    progress.line         line being executed
    progress.lines        lines in the loaded file
    progress.running      1 while a program is running
"""

import os
import time

import hal
import linuxcnc

UPDATE_INTERVAL = 0.2

# Below this fraction the extrapolation is dominated by spin-up and start-up
# moves and produces wild numbers, so no estimate is published yet.
MIN_FRACTION_FOR_ESTIMATE = 0.02

PINS = (
    "percent",
    "elapsed-min",
    "remain-min",
    "total-min",
    "line",
    "lines",
    "running",
)


def count_lines(path):
    """Lines in the file that can produce motion; blanks and comments cannot."""
    if not path or not os.path.exists(path):
        return 0
    total = 0
    try:
        with open(path, "r", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped and not stripped.startswith((";", "(")):
                    total += 1
    except OSError:
        return 0
    return total


def main():
    component = hal.component("progress")
    for name in PINS:
        component.newpin(name, hal.HAL_FLOAT, hal.HAL_OUT)
    component.ready()

    # The component is loaded before milltask, so the status channel is not
    # there yet on the first passes through the loop.
    stat = None

    current_file = None
    total_lines = 0
    elapsed = 0.0
    was_running = False
    last_tick = time.time()

    while True:
        time.sleep(UPDATE_INTERVAL)

        now = time.time()
        delta = now - last_tick
        last_tick = now

        try:
            if stat is None:
                stat = linuxcnc.stat()
            stat.poll()
        except (linuxcnc.error, OSError):
            stat = None
            continue

        if stat.file != current_file:
            current_file = stat.file
            total_lines = count_lines(current_file)
            elapsed = 0.0

        running = (stat.task_mode == linuxcnc.MODE_AUTO
                   and stat.interp_state != linuxcnc.INTERP_IDLE)
        if running and not was_running:
            elapsed = 0.0
        if running and not stat.paused:
            elapsed += delta
        was_running = running

        line = stat.motion_line or stat.current_line or 0
        fraction = min(line / total_lines, 1.0) if total_lines else 0.0

        if fraction >= MIN_FRACTION_FOR_ESTIMATE and elapsed > 0:
            total_estimate = elapsed / fraction
        else:
            total_estimate = 0.0

        component["percent"] = fraction * 100.0
        component["elapsed-min"] = elapsed / 60.0
        component["remain-min"] = max(total_estimate - elapsed, 0.0) / 60.0
        component["total-min"] = total_estimate / 60.0
        component["line"] = line
        component["lines"] = total_lines
        component["running"] = 1.0 if running else 0.0


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(0)
