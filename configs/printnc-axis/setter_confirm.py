#!/usr/bin/env python3
"""Confirmation dialogs for the touch off buttons.

Each button drives a request pin here instead of halui directly. On a rising
edge the dialog is shown, naming the axis, and the go pin is pulsed only on OK.
The go pins drive halui.mdi-command-NN, so the commands themselves stay in the
ini file.

The dialog is built once and hidden between uses rather than rebuilt per press.
Building it costs one X round trip per widget, which is slow when the GUI is
forwarded over the network.
"""

import tkinter

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


class Dialog(object):
    def __init__(self, root):
        self.answer = False
        self.done = tkinter.BooleanVar(root, False)

        self.top = tkinter.Toplevel(root)
        self.top.withdraw()
        self.top.title("Touch off")
        self.top.resizable(False, False)
        self.top.attributes("-topmost", True)
        self.top.protocol("WM_DELETE_WINDOW", self.cancel)

        self.label = tkinter.Label(
            self.top, justify="left", padx=25, pady=20, font=("Helvetica", 11)
        )
        self.label.pack()

        row = tkinter.Frame(self.top)
        row.pack(pady=(0, 18))
        tkinter.Button(row, text="Cancel", width=10, command=self.cancel).pack(
            side="left", padx=6
        )
        tkinter.Button(row, text="OK", width=10, command=self.confirm).pack(
            side="left", padx=6
        )

    def cancel(self):
        self.answer = False
        self.done.set(True)

    def confirm(self):
        self.answer = True
        self.done.set(True)

    def ask(self, question):
        self.label.config(text=question)
        self.done.set(False)
        self.top.deiconify()
        self.top.lift()
        self.top.wait_variable(self.done)
        self.top.withdraw()
        return self.answer


comp = hal.component("confirm")
for axis, _ in BUTTONS:
    comp.newpin("%s-req" % axis, hal.HAL_BIT, hal.HAL_IN)
    comp.newpin("%s-go" % axis, hal.HAL_BIT, hal.HAL_OUT)
comp.ready()

root = tkinter.Tk()
root.withdraw()
dialog = Dialog(root)

previous = dict((axis, False) for axis, _ in BUTTONS)
busy = [False]


def release(axis):
    comp["%s-go" % axis] = False


def poll():
    if not busy[0]:
        for axis, question in BUTTONS:
            pressed = comp["%s-req" % axis]
            if pressed and not previous[axis]:
                busy[0] = True
                try:
                    confirmed = dialog.ask(question)
                finally:
                    busy[0] = False
                if confirmed:
                    comp["%s-go" % axis] = True
                    root.after(PULSE_MS, release, axis)
                previous[axis] = comp["%s-req" % axis]
                break
            previous[axis] = pressed
    root.after(POLL_MS, poll)


root.after(POLL_MS, poll)
try:
    root.mainloop()
except KeyboardInterrupt:
    pass
