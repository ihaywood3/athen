#!/usr/bin/python

from Tkinter import *
import ttk

# tooltip object lifted from https://www.daniweb.com/programming/software-development/code/484591/a-tooltip-class-for-tkinter
class Tooltip(object):
    '''
    create a tooltip for a given widget
    '''
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)

    def enter(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(self.tw, text=self.text, justify='left',
                       background='yellow', relief='solid', borderwidth=1,
                       font=("times", "8", "normal"))
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.tw:
            self.tw.destroy()


root = Tk()
root.wm_title("ATHEN")


username = StringVar(root)
password = StringVar(root)
download_path = StringVar(root)
upload_path = StringVar(root)
status = StringVar(root)

root.columnconfigure(1,weight=1)
ttk.Label(root,text="Username").grid(row=0,column=0)
username_entry = ttk.Entry(root,textvariable=username)
username_entry.grid(row=0,column=1,columnspan=3,sticky=(E,W),padx=3,pady=3)
Tooltip(username_entry,"The assigned username for the ATHEN server")
ttk.Label(root,text="Password").grid(row=1,column=0)
ttk.Entry(root,textvariable=password,show="*").grid(row=1,column=1,columnspan=3,sticky=(E,W),padx=3,pady=3)
ttk.Label(root,text="Download").grid(row=2,column=0)
ttk.Entry(root,textvariable=download_path).grid(row=2,column=1,columnspan=2,sticky=(E,W),padx=3,pady=3)
ttk.Button(root,text="Open...",command=None).grid(row=2,column=3)
ttk.Label(root,text="Upload").grid(row=3,column=0)
ttk.Entry(root,textvariable=upload_path).grid(row=3,column=1,columnspan=2,sticky=(E,W),padx=3,pady=3)
ttk.Button(root,text="Open...",command=None).grid(row=3,column=3)
ttk.Label(root,text="Status").grid(row=4,column=0)
ttk.Entry(root,textvariable=status,state='readonly').grid(row=4,column=1,columnspan=3,sticky=(E,W),padx=3,pady=3)
ttk.Button(root,text="Save",command=None).grid(row=5,column=1,padx=3,pady=3)
ttk.Button(root,text="Quit",command=root.destroy).grid(row=5,column=2,padx=3,pady=3)
root.mainloop()
