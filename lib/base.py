"""
The base of the local client
UDP communication and loading configuration
config can be reloaded by UDP signal
"""

from socket import *
import threading, os, os.path, sqlite3, logging, sys

PORT=62347
DBDEF=[
    'CREATE TABLE config (key text, value text)',
    'CREATE TABLE files (path text, origin text, ref text)']


QUIT_NOTIFY=0  # if need to quit move to "quit soft"
QUIT_SOFT=1  # quit when convient for the client
QUIT_NOW=2 # quite using sys.exit()

class DB:

    def __init__(self,dbpath):
        if os.access(dbpath,os.R_OK):
            db_exist = True
            if not os.access(dbpath,os.W_OK):
                logging.critical("Cannot write to config DB")
                sys.exit(1)
        self.db = sqlite3.connect(dbpath)
        if not db_exist:
            c = self.db.cursor()
            for i in DBDEF: c.execute(i)
            c.close()
            self.db.commit()


    def __setitem__(self, key, value):
        c = self.db.cursor()
        c.execute("SELECT 1 FROM config WHERE key=?",(key,))
        if c.rowcount == 0:
            c.execute("INSERT INTO config(key, value) VALUES (?, ?)",(key, value))
        else:
            c.execute("UPDATE config SET value=? WHERE key=?",(value, key))
        c.close()
        self.db.commit()
        self.config[key] = value

    def __getitem__(self, key):
        c = self.db.cursor()
        c.execute("SELECT value FROM config WHERE key=?",(key,))
        if c.rowcount == 0: return None
        r = c.fetchone()[0]
        c.close()
        return r

    def get_files(self):
        c = self.db.cursor()
        c.execute("SELECT path, origin, ref FROM files")
        for i in c.fetchall():
            yield {'path':i[0],'origin':i[1],'ref':i[2]}
        c.close()

    def add_file(self, path, origin, ref):
        c = self.db.cursor()
        c.execute("INSERT INTO files (path, origin, ref) VALUES (?, ?, ?)", (path, origin, ref))
        c.close()
        self.db.commit()

    def delete_file(self, path):
        c = self.db.cursor()
        c.execute("DELETE FROM files WHERE path=?", (path,))
        c.close()
        self.db.commit()

class UDPServer:
        
    def __init__(self):
        self.listen_thread()
        self.status = "Initialising"
        self.quitmode = QUIT_NOTIFY
        self.config_dirty = False

    def listen_forever(self):
        self.sock = socket(AF_INET,SOCK_DGRAM) # UDP
        self.sock.bind(('127.0.0.1',PORT))
        while True:
            data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
            data = data.strip()
            getattr(self,'msg_'+data) (addr)

    def listen_thread(self):
        self.worker = threading.Thread(target=self.listen_forever)
        self.worker.start()
        
    def set_status(self,status):
        self.status = status

    def msg_STATUS(self, addr):
        self.sock.sendto(self.status+'\r\n', addr)

    def msg_RELOAD(self, addr):
        self.config_dirty = True

    def msg_QUIT(addr):
        if self.quitmode == QUIT_NOW:
            sys.exit(0)
        self.quitmode = QUIT_SOFT

    def should_quit(self):
        return (self.quitmode == QUIT_SOFT)

class UDPClient:

    def __init__(self):
        self.sock = socket(AF_INET,SOCK_DGRAM)
        self.sock.settimeout(1.0)
        
    def get_status(self):
        self.sock.sendto("STATUS\r\n",('127.0.0.1',PORT))
        try:
            data, addr = self.sock.recvfrom(1024)
        except socket.error:
            return None
        return str(data).strip()
        
    def reload(self):
        self.sock.sendto("RELOAD\r\n",('127.0.0.1',PORT))
    
    def quit(self):
        self.sock.sendto("QUIT\r\n",('127.0.0.1',PORT))
