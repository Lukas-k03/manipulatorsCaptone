import tkinter as tk

# Create the main window
window = tk.Tk()
window.title("Tkinter Test Program")

# Create a label
label = tk.Label(window, text="Hello, Tkinter!")
label.pack(pady=20)

# Create a button
button = tk.Button(window, text="Click Me!", command=lambda: label.config(text="Button Clicked!"))
button.pack()

# Start the main event loop
window.mainloop()
