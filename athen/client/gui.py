#!/usr/bin/python3

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
            font=("times", "10", "normal"),
        )
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.tw:
            self.tw.destroy()


def save_config():
    for k in dialog_dialog_vars:
        s = dialog_dialog_vars[k].get()
        db.set_config(k, s)
    db.set_config("config_time", time.asctime())
    db.save_config()


def save_code():
    pass




def gui_setup(root):
    # now set up GUI
    global dialog_vars
    def gui_quit():
        root.destroy()


    def opendir(path):
        newpath = filedialog.askdirectory(
            parent=root, title="Set " + path, initialdir=dialog_vars[path].get() or "/"
        )
        if newpath:
            dialog_vars[path].set(newpath)

    root.wm_title("ATHEN")
    root.protocol("WM_DELETE_WINDOW", gui_quit)
    dialog_vars = {}
    dialog_vars["name"] = StringVar(root)
    dialog_vars["line"] = StringVar(root)
    dialog_vars["city"] = StringVar(root)
    dialog_vars["postalCode"] = StringVar(root)
    dialog_vars["state"] = StringVar(root)
    dialog_vars["type"] = StringVar(root)
    dialog_vars["activation_code"] = StringVar(root)
    dialog_vars[""] = StringVar(root)
    dialog_vars["download_path"] = StringVar(root)
    dialog_vars["upload_path"] = StringVar(root)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=BOTH)
    config_tab = Frame(notebook)
    notebook.add(config_tab, text="Configuration")
    org_tab = Frame(notebook)
    notebook.add(org_tab, text="Practice Details")
    members_tab = Frame(notebook)
    notebook.add(members_tab, text="Members")
    log_tab = Frame(notebook)
    notebook.add(log_tab, text="Event Log")

    # set up config tab
    config_tab.columnconfigure(1, weight=1)

    ttk.Label(config_tab, text="Activation code").grid(row=0, column=0)
    ac_entry = ttk.Entry(config_tab, textvariable=dialog_vars["activation_code"], show="*")
    ac_entry.grid(row=0, column=1, columnspan=2, sticky=(E, W), padx=3, pady=3)
    Tooltip(
        ac_entry,
        "The activation code that will be posted out to the practice's address",
    )
    ttk.Button(config_tab, text="Save...", command=save_code).grid(row=0, column=3)

    ttk.Label(config_tab, text="Download").grid(row=1, column=0)
    d_entry = ttk.Entry(config_tab, textvariable=dialog_vars["download_path"])
    d_entry.grid(row=1, column=1, columnspan=2, sticky=(E, W), padx=3, pady=3)
    Tooltip(d_entry, "The directory in which received files will be saved")
    ttk.Button(
        config_tab, text="Open...", command=lambda: opendir("download_path")
    ).grid(row=1, column=3)

    ttk.Label(config_tab, text="Upload").grid(row=2, column=0)
    u_entry = ttk.Entry(config_tab, textvariable=dialog_vars["upload_path"])
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

    # set up Practice tab
    org_tab.columnconfigure(1, weight=1)

    ttk.Label(org_tab,
              text="Practice Address",
              font="wxHeadingFont").grid(row=0, column=0, columnspan=3, pady=8) 
  
    ttk.Label(org_tab, text="Practice name").grid(row=1, column=0)
    pn_entry = ttk.Entry(org_tab, textvariable=dialog_vars["name"])
    pn_entry.grid(row=1, column=1, columnspan=7, sticky=(E, W), padx=3, pady=3)
    Tooltip(
        pn_entry,
        "Practice name. This is listed in the public directory.",
    )

    ttk.Label(org_tab, text="Street address").grid(row=2, column=0)
    l_entry = ttk.Entry(org_tab, textvariable=dialog_vars["line"])
    l_entry.grid(row=2, column=1, columnspan=7, sticky=(E, W), padx=3, pady=3)
    Tooltip(
        l_entry,
        "Street name and number. This is NOT listed in the public directory.",
    )

    ttk.Label(org_tab, text="Suburb").grid(row=3, column=0)
    c_entry = ttk.Entry(org_tab, textvariable=dialog_vars["city"])
    c_entry.grid(row=3, column=1, columnspan=7, sticky=(E, W), padx=3, pady=3)
    Tooltip(
        c_entry,
        "City. This is listed in the public directory.",
    )

    ttk.Label(org_tab, text="Postcode").grid(row=4, column=0)
    pc_entry = ttk.Entry(org_tab, textvariable=dialog_vars["postalCode"])
    pc_entry.grid(row=4, column=1, sticky=(E, W), padx=3, pady=3)
    Tooltip(
        pc_entry,
        "Four-digit postcode. This is listed in the public directory.",
    )   
    
    ttk.Label(org_tab, text="State/Territory").grid(row=4, column=2, columnspan=3)
    st_cb = ttk.Combobox(org_tab, textvariable=dialog_vars["state"])
    st_cb.grid(row=4, column=5, sticky=(E, W), padx=3, pady=3, columnspan=3)
    st_cb["values"] = ("Western Australia", "South Australia", "Northern Territory", "Queensland", 
    "New South Wales", "Australian Capital Territory", "Victoria", "Tasmania")
    st_cb.state(["readonly"])
    st_cb.bind("<<ComboboxSelected>>", lambda _: st_cb.selection_clear())
    Tooltip(
        st_cb,
        "State/Territory. This is listed in the public directory.")
    

    ttk.Label(org_tab,
              text="Practice Clinicians",
              font="wxHeadingFont").grid(row=5, column=0, columnspan=3, pady=8)

    members_list = StringVar()
    m_lb = Listbox(org_tab, listvariable=members_list)
    m_lb.grid(row=6, column=0, rowspan=5, columnspan=2, sticky=(E,N,S,W))

    given_v = StringVar()
    ttk.Label(org_tab, text="Given name").grid(row=6,column=2,columnspan=3)
    given_entry = ttk.Entry(org_tab, textvariable=given_v)
    given_entry.grid(row=6, column=5, columnspan=3)

    surname_v = StringVar()
    ttk.Label(org_tab, text="Surname").grid(row=7,column=2,columnspan=3)
    sur_entry = ttk.Entry(org_tab, textvariable=surname_v)
    sur_entry.grid(row=7, column=5, columnspan=3)

    mpn_v = StringVar()
    ttk.Label(org_tab, text="Provider number").grid(row=8,column=2,columnspan=3)
    mpn_entry = ttk.Entry(org_tab, textvariable=mpn_v)
    mpn_entry.grid(row=8, column=5, columnspan=3)

    new_b = ttk.Button(org_tab, text="New")
    new_b.grid(row=9, column=2, columnspan=2, sticky=(E,))
    save_b = ttk.Button(org_tab, text="Save")
    save_b.grid(row=9, column=4, columnspan=2, sticky=(E,W))
    del_b = ttk.Button(org_tab, text="Delete")
    del_b.grid(row=9, column=6, columnspan=2, sticky=(W,))

    upload_b = ttk.Button(org_tab, text="Upload")
    upload_b.grid(row=11, column=1, pady=12)
    
    # set up Log tab_
    log_text = Text(log_tab)
    log_text.tag_config("timestamp", font=("times", 10, "bold"))
    log_text.tag_config("normal", font=("times", 10, ""))
    log_text.tag_config("warning", font=("times", 10, ""), foreground="red")
    log_text.tag_config("error", font=("times", 10, "bold"), foreground="red")
    log_text.pack(fill=BOTH)



# initialise the config screen from the DB
# configs = db.get_all_configs()
# for k in list(dialog_vars.keys()):
#    if k in configs:
#        dialog_vars[k].set(configs[k])


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

