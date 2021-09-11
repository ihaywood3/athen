#!/usr/bin/python

try:
    from tkinter import *
    import tkinter.ttk as ttk
    import tkinter.filedialog as filedialog
except ImportError:
    from Tkinter import *
    import ttk
    import tkFileDialog as filedialog

import time

# tooltip object lifted from https://www.daniweb.com/programming/software-development/code/484591/a-tooltip-class-for-tkinter
class Tooltip(object):
    """
    create a tooltip for a given widget
    """

    def __init__(self, widget, text="widget info"):
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
        label = Label(
            self.tw,
            text=self.text,
            justify="left",
            background="yellow",
            relief="solid",
            borderwidth=1,
            font=("times", "8", "normal"),
        )
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.tw:
            self.tw.destroy()


root = Tk()


def save_config():
    for k in vars:
        s = vars[k].get()
        db.set_config(k, s)
    db.set_config("config_time", time.asctime())
    db.save_config()


def save_code():
    pass


def gui_quit():
    root.destroy()


def opendir(path):
    newpath = filedialog.askdirectory(
        parent=root, title="Set " + path, initialdir=vars[path].get() or "/"
    )
    if newpath:
        vars[path].set(newpath)


def gui_setup():
    # now set up GUI

    root.wm_title("ATHEN")
    root.protocol("WM_DELETE_WINDOW", gui_quit)
    vars = {}
    vars["name"] = StringVar(root)
    vars["line"] = StringVar(root)
    vars["city"] = StringVar(root)
    vars["postalCode"] = StringVar(root)
    vars["state"] = StringVar(root)
    vars["type"] = StringVar(root)
    vars["activation_code"] = StringVar(root)
    vars[""] = StringVar(root)
    vars["download_path"] = StringVar(root)
    vars["upload_path"] = StringVar(root)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=BOTH)
    config_tab = Frame(notebook)
    notebook.add(config_tab, text="Config")
    org_tab = Frame(notebook)
    notebook.add(org_tab, text="Practice")
    members_tab = Frame(notebook)
    notebook.add(members_tab, text="Members")
    log_tab = Frame(notebook)
    notebook.add(log_tab, text="Log")

    # set up config tab
    config_tab.columnconfigure(1, weight=1)

    ttk.Label(config_tab, text="Activation code").grid(row=0, column=0)
    ac_entry = ttk.Entry(config_tab, textvariable=vars["activation_code"], show="*")
    ac_entry.grid(row=0, column=1, columnspan=2, sticky=(E, W), padx=3, pady=3)
    Tooltip(
        ac_entry,
        "The activation code that will be posted out to the practice's address",
    )
    ttk.Button(config_tab, text="Save...", command=save_code).grid(row=0, column=3)

    ttk.Label(config_tab, text="Download").grid(row=1, column=0)
    d_entry = ttk.Entry(config_tab, textvariable=vars["download_path"])
    d_entry.grid(row=1, column=1, columnspan=2, sticky=(E, W), padx=3, pady=3)
    Tooltip(d_entry, "The directory in which received files will be saved")
    ttk.Button(
        config_tab, text="Open...", command=lambda: opendir("download_path")
    ).grid(row=1, column=3)

    ttk.Label(config_tab, text="Upload").grid(row=2, column=0)
    u_entry = ttk.Entry(config_tab, textvariable=vars["upload_path"])
    u_entry.grid(row=2, column=1, columnspan=2, sticky=(E, W), padx=3, pady=3)
    Tooltip(u_entry, "The directory that will be read for files to send")
    ttk.Button(config_tab, text="Open...", command=lambda: opendir("upload_path")).grid(
        row=2, column=3
    )

    ttk.Button(config_tab, text="Save", command=save_config).grid(
        row=4, column=1, padx=3, pady=3
    )
    ttk.Button(config_tab, text="Quit", command=gui_quit).grid(
        row=4, column=2, padx=3, pady=3
    )

    # set up Log tab
    log_text = Text(log_tab)
    log_text.tag_config("timestamp", font=("times", 10, "bold"))
    log_text.tag_config("normal", font=("times", 10, ""))
    log_text.tag_config("warning", font=("times", 10, ""), foreground="red")
    log_text.tag_config("error", font=("times", 10, "bold"), foreground="red")
    log_text.pack(fill=BOTH)


# initialise the config screen from the DB
# configs = db.get_all_configs()
# for k in list(vars.keys()):
#    if k in configs:
#        vars[k].set(configs[k])


def refresh_log():
    """Refresh the log"""
    logs = db.get_log()
    log_text.config(state=NORMAL)
    # log_text.delete(1.0, END)
    for i in guilogger.dequeue():
        text = "[{}] ".format(i[0])
        log_text.insert(END, text, "timestamp")
        text = "{}\n".format(i[2])
        tag = "normal"
        if i[1] == 1:
            tag = "warning"
        if i[1] == 2:
            tag = "error"
        log_text.insert(END, text, tag)
        # FIXME: bold the date and different colours for errors/warnings
    log_text.config(state=DISABLED)
    log_text.after(TICK_TIME, refresh_log)


gui_setup()

# run the main loop
root.mainloop()
