import base, imap, signal, logging

db = base.DB()
imap = imap.Emailer(db)

def handle_SIGTERM(sig,frame):
    imap.running = False
    logging.debug("received SIGTERM")
    
def handle_SIGUSR1(sig,frame):
    logging.debug("received SIGUSR1")

if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger().addHandler(base.SQLiteHandler(db))
    signal.signal(signal.SIGUSR1,handle_SIGUSR1)
    signal.signal(signal.SIGTERM,handle_SIGTERM)
    imap.loop()
