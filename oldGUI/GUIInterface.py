import tkinter as tk
from gCodeParser import generate_gcode

def Slider(value):
    x = x_slider.get()
    y = y_slider.get()
    z = z_slider.get()
    a = a_slider.get()
    b = b_slider.get()
    gcode_text = str(generate_gcode(x, y, z, a, b))  # Generate G-code dynamically
    label.config(text=gcode_text)  # Update label
    

# Create the main window
window = tk.Tk()
window.title("Tkinter Test Program")

# Create a label
label = tk.Label(window, text="Hello, Tkinter!")
label.pack(pady=20)

# Create a button
x_slider = tk.Scale(window, from_=0, to=100, orient="horizontal", label="X" ,command=Slider)
x_slider.pack()
y_slider = tk.Scale(window, from_=0, to=100, orient="horizontal", label="Y",command=Slider)
y_slider.pack()
z_slider = tk.Scale(window, from_=0, to=100, orient="horizontal", label="Z",command=Slider)
z_slider.pack()
a_slider = tk.Scale(window, from_=0, to=100, orient="horizontal", label="A",command=Slider)
a_slider.pack()
b_slider = tk.Scale(window, from_=0, to=100, orient="horizontal", label="B ",command=Slider)
b_slider.pack()

# Start the main event loop
window.mainloop()
