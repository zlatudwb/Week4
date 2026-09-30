import tkinter as tk
from tkinter import ttk

KGF_TO_NEWTON = 9.81


def to_newtons(value, unit):
    if unit == "kN":
        return value * 1000
    if unit == "kgf":
        return value * KGF_TO_NEWTON
    return value


def from_newtons(newtons, unit):
    if unit == "kN":
        return newtons / 1000
    if unit == "kgf":
        return newtons / KGF_TO_NEWTON
    return newtons


def convert_and_display(value_entry, input_unit_box, output_unit_box, result_label, error_label):
    try:
        value = float(value_entry.get().strip())
    except ValueError:
        result_label.config(text="")
        error_label.config(text="\uc624\ub958: \uc22b\uc790\ub97c \uc785\ub825\ud558\uc138\uc694.")
        value_entry.focus_set()
        return

    input_unit = input_unit_box.get()
    output_unit = output_unit_box.get()
    result = from_newtons(to_newtons(value, input_unit), output_unit)
    result_label.config(text=f"\uacb0\uacfc\n{result:,.2f} {output_unit}")
    error_label.config(text="")


def main():
    root = tk.Tk()
    root.title("\ud798 \ub2e8\uc704 \ubcc0\ud658 \uacc4\uc0b0\uae30")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=20)
    frame.grid(row=0, column=0)
    ttk.Label(frame, text="\ud798 \ub2e8\uc704 \ubcc0\ud658 \uacc4\uc0b0\uae30", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))

    ttk.Label(frame, text="\uc22b\uc790").grid(row=1, column=0, sticky="w", pady=5)
    value_entry = ttk.Entry(frame, width=24)
    value_entry.grid(row=1, column=1, pady=5)

    units = ("kN", "N", "kgf")
    ttk.Label(frame, text="\uc785\ub825 \ub2e8\uc704").grid(row=2, column=0, sticky="w", pady=5)
    input_unit_box = ttk.Combobox(frame, values=units, state="readonly", width=21)
    input_unit_box.set("kN")
    input_unit_box.grid(row=2, column=1, pady=5)

    ttk.Label(frame, text="\ubcc0\ud658 \ub2e8\uc704").grid(row=3, column=0, sticky="w", pady=5)
    output_unit_box = ttk.Combobox(frame, values=units, state="readonly", width=21)
    output_unit_box.set("N")
    output_unit_box.grid(row=3, column=1, pady=5)

    result_label = ttk.Label(frame, text="", justify="center", anchor="center")
    result_label.grid(row=5, column=0, columnspan=2, pady=(15, 5))
    error_label = ttk.Label(frame, text="", foreground="red")
    error_label.grid(row=6, column=0, columnspan=2, pady=(0, 5))

    convert_command = lambda: convert_and_display(
        value_entry, input_unit_box, output_unit_box, result_label, error_label
    )
    ttk.Button(frame, text="\ubcc0\ud658", command=convert_command).grid(
        row=4, column=0, columnspan=2, pady=12, ipadx=20
    )
    value_entry.bind("<Return>", lambda _event: convert_command())
    value_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()

