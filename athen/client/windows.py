# Import the required libraries
from tkinter import *
from pystray import MenuItem as item
import pystray
from PIL import Image, ImageTk

from athen.client import gui

ICON_PATH="C:\\Users\\Smartbox\\Downloads\\athen.ico" 

# Create an instance of tkinter frame or window
win=Tk()
gui.gui_setup(win)

# Define a function for quit the window
def quit_window(icon, item):
   icon.stop()
   win.destroy()

# Define a function to show the window again
def show_window(icon, item):
   icon.stop()
   win.after(0,win.deiconify())

# Hide the window and show on the system taskbar
def hide_window():
   win.withdraw()
   image=Image.open(ICON_PATH)
   menu=pystray.Menu(item('Quit', quit_window), item('Show', show_window, default=True))
   icon=pystray.Icon("ATHEN", image, "ATHEN", menu=menu)
   icon.run()

win.protocol('WM_DELETE_WINDOW', hide_window)
win.iconbitmap(ICON_PATH)

win.mainloop()
