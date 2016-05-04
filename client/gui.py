#!/usr/bin/python

from Tkinter import *
import logging, pdb, time
import ttk

import base

db = base.DB()

TICK_TIME=2000

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



    
def save_config():
    #pdb.set_trace()
    for k in vars:
        s = vars[k].get()
        db.set_config(k, s)
    db.set_config('config_time',time.asctime())
        
def quit():
    db.add_log(0, "GUI client exited")
    root.destroy()

# now set up GUI

root = Tk()
root.wm_title("ATHEN")
root.protocol("WM_DELETE_WINDOW", quit)
vars = {}
vars['username'] = StringVar(root)
vars['password'] = StringVar(root)
vars['download_path'] = StringVar(root)
vars['upload_path'] = StringVar(root)

notebook = ttk.Notebook(root)
notebook.pack(fill=BOTH)
config_tab = Frame(notebook)
notebook.add(config_tab,text="Config")
log_tab = Frame(notebook)
notebook.add(log_tab,text="Log")

# set up config tab
config_tab.columnconfigure(1,weight=1)
ttk.Label(config_tab,text="Username").grid(row=0,column=0)
username_entry = ttk.Entry(config_tab,textvariable=vars['username'])
username_entry.grid(row=0,column=1,columnspan=3,sticky=(E,W),padx=3,pady=3)
Tooltip(username_entry,"The assigned username for the ATHEN server")
ttk.Label(config_tab,text="Password").grid(row=1,column=0)
ttk.Entry(config_tab,textvariable=vars['password'],show="*").grid(row=1,column=1,columnspan=3,sticky=(E,W),padx=3,pady=3)
ttk.Label(config_tab,text="Download").grid(row=2,column=0)
ttk.Entry(config_tab,textvariable=vars['download_path']).grid(row=2,column=1,columnspan=2,sticky=(E,W),padx=3,pady=3)
ttk.Button(config_tab,text="Open...",command=None).grid(row=2,column=3)
ttk.Label(config_tab,text="Upload").grid(row=3,column=0)
ttk.Entry(config_tab,textvariable=vars['upload_path']).grid(row=3,column=1,columnspan=2,sticky=(E,W),padx=3,pady=3)
ttk.Button(config_tab,text="Open...",command=None).grid(row=3,column=3)
ttk.Button(config_tab,text="Save",command=save_config).grid(row=4,column=1,padx=3,pady=3)
ttk.Button(config_tab,text="Quit",command=quit).grid(row=4,column=2,padx=3,pady=3)

# set up Log tab
log_text = Text(log_tab)
log_text.tag_config('timestamp',font=('times',10,'bold'))
log_text.tag_config('normal',font=('times',10,''))
log_text.tag_config('warning',font=('times',10,''),foreground='yellow')
log_text.tag_config('error',font=('times',10,'bold'),foreground='red')
log_text.pack(fill=BOTH)

# initialise the config screen from the DB
configs = db.get_all_configs()
for k in vars.keys():
    if k in configs:
        vars[k].set(configs[k])
    
def refresh_log():
    """Refresh the log"""
    logs = db.get_log()
    log_text.config(state=NORMAL)
    log_text.delete(1.0, END)
    for i in logs:
        text = "[{}] ".format(i[0])
        log_text.insert(END,text,"timestamp")
        text = "{}\n".format(i[2])
        tag = "normal"
        if i[1] == 1: tag = "warning"
        if i[1] == 2: tag = "error"
        log_text.insert(END, text, tag)
        # FIXME: bold the date and different colurs for errors/warnings

    log_text.config(state=DISABLED)
    log_text.after(TICK_TIME, refresh_log)

db.add_log(0, "client starting")

# initialise the log by called a tick
refresh_log()

# run the main loop
root.mainloop()
