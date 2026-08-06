#!/usr/bin/env python3
"""Confirmation dialogs for the touch off buttons.

Each button drives a request pin here instead of halui directly. On a rising
edge the matching dialog is shown, naming the axis, and the go pin is pulsed
only on OK. The go pins drive halui.mdi-command-NN, so the commands themselves
stay in the ini file.
"""

import tkinter
from tkinter import messagebox

import hal

BUTTONS = (
    ("x", "Set X zero at the current position?"),
    ("y", "Set Y zero at the current position?"),
    (
        "z",
        "Set Z zero at the current position?\n\n"
        "This also invalidates the setter calibration.",
    ),
)

POLL_MS = 50
PULSE_MS = 200

comp = hal.component("confirm")
for axis, _ in BUTTONS:
    comp.newpin("%s-req" % axis, hal.HAL_BIT, hal.HAL_IN)
    comp.newpin("%s-go" % axis, hal.HAL_BIT, hal.HAL_OUT)
comp.ready()

root = tkinter.Tk()
root.withdraw()
root.attributes("-topmost", True)

previous = dict((axis, False) for axis, _ in BUTTONS)


def release(axis):
    comp["%s-go" % axis] = False


def poll():
    for axis, question in BUTTONS:
        pressed = comp["%s-req" % axis]
        if pressed and not previous[axis]:
            if messagebox.askokcancel("Touch off", question):
                comp["%s-go" % axis] = True
                root.after(PULSE_MS, release, axis)
        previous[axis] = comp["%s-req" % axis]
    root.after(POLL_MS, poll)


root.after(POLL_MS, poll)
try:
    root.mainloop()
except KeyboardInterrupt:
    pass
