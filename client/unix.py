import os, signal, sys, logging

if os.path.exists("/home/ian/athen/lib"):
    sys.path.append("/home/ian/athen/lib")
else:
    sys.path.append("/usr/lib/athen/lib")

import base, imap



def handle_SIGTERM(sig,frame):
    global imap
    imap.set_external_quit()
    logging.debug("received SIGTERM")
    
def handle_SIGUSR1(sig,frame):
    global imap
    imap.set_external_reconfigure()
    logging.debug("received SIGUSR1")

if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    db = base.DB()
    logging.getLogger().addHandler(base.SQLiteHandler(db))
    logging.getLogger().addHandler(logging.FileHandler('/var/log/athen/daemon.log'))
    imap = imap.Emailer(db)
    signal.signal(signal.SIGUSR1,handle_SIGUSR1)
    signal.signal(signal.SIGTERM,handle_SIGTERM)
    imap.loop()
