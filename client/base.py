"""
The base of the local client
UDP communication and loading configuration
config can be reloaded by UDP signal
"""

from socket import *
import threading, os, os.path, sqlite3, logging, sys, time

PORT=62347
DBDEF=[
    'CREATE TABLE config (key text, value text)',
    'CREATE TABLE files (path text, origin text, ref text)',
    '''CREATE TABLE sent (path text, 
        dest text, 
        ref text, 
        status text, 
        comment text, 
        stamp text default current_timestamp)''',
    '''
    CREATE TABLE log (
       stamp text default current_timestamp, 
       severity integer, notes text)'''
    ]


QUIT_NOTIFY=0  # if need to quit move to "quit soft"
QUIT_SOFT=1  # quit when convient for the client
QUIT_NOW=2 # quite using sys.exit()

TRY_PATHS=['C:\\Program Files\\ATHEN',
           'C:\\ATHEN',
           '/var/lib/athen/']

class PermanentError(Exception):
    """An error that won't get fixed until the user changes the settings"""
    pass
    
class TempError(Exception):
    """An error that might not recur if we try again"""
    pass


class DB:

    def __init__(self):
        dbpath = None
        for i in TRY_PATHS:
            if os.access(i,os.R_OK):
                dbpath = i
        if dbpath is None:
            logging.critical("Cannot find a path for DB")
            raise Exception("Cannot find path for DB")
        self.dbpath = dbpath
        dbpath = os.path.join(dbpath,'config.sq3')
        db_exist = os.access(dbpath,os.R_OK)
        self.db = sqlite3.connect(dbpath)
        if not db_exist:
            c = self.db.cursor()
            for i in DBDEF: c.execute(i)
            c.close()
            self.db.commit()


    def set_config(self, key, value):
        c = self.db.cursor()
        c.execute("SELECT key FROM config WHERE key=?",(key,))
        if len(c.fetchall()) == 0:
            logging.error("INSERT {} {}".format(key, value))
            c.execute("INSERT INTO config (key, value) VALUES (?, ?)",(key, value))
        else:
            logging.error("UPDATE {} {} rowcount {}".format(key, value, c.rowcount))
            c.execute("UPDATE config SET value=? WHERE key=?",(value, key))
        c.close()
        self.db.commit()

    def get_config(self, key):
        c = self.db.cursor()
        c.execute("SELECT value FROM config WHERE key=?",(key,))
        if c.rowcount == 0: return None
        r = c.fetchone()[0]
        c.close()
        return r
    
    def get_ref_number(self):
        """Return a five-digit monotonically increasing number for the 
        local system"""
        n = self.get_config('lab_reference')
        if n is None: 
            n = 0
        else:
            n = int(n)
        n = n+1
        if n > 99999:
            n = 1  # loop back to one
        self.set_config('lab_reference',str(n))
        return "{:0>5}".format(n)
    
    def get_all_configs(self):
        r = {}
        c = self.db.cursor()
        c.execute("SELECT key, value FROM config")
        for i in c.fetchall():
            r[i[0]] = i[1]
        c.close()
        return r

    def get_files(self):
        c = self.db.cursor()
        c.execute("SELECT path, origin, ref FROM files")
        for i in c.fetchall():
            yield {'path':i[0],'origin':i[1],'ref':i[2]}
        c.close()
        
    def check_file(self,path):
        c = self.db.cursor()
        c.execute("SELECT path, origin, ref FROM files WHERE path=?", (path,))
        r = c.fetchone()
        c.close()
        return r

    def add_file(self, path, origin, ref):
        c = self.db.cursor()
        c.execute("INSERT INTO files (path, origin, ref) VALUES (?, ?, ?)", (path, origin, ref))
        c.close()
        self.db.commit()
        
    def add_sent_file(self, path, dest, ref):
        c = self.db.cursor()
        c.execute("INSERT INTO sent_files (path, dest, ref, status) VALUES (?, ?, ?, 1)", (path, dest, ref))
        c.close()
        self.db.commit()
        
    def set_file_status(self, ref, status, comment):
        c = self.db.cursor()
        c.execute("SELECT * FROM sent_files WHERE ref=?",(ref,))
        if c.fetchone() is None:
            raise Exception("No sent file for {}".format(ref))
        c.execute("UPDATE sent_files SET status=?, comment=? WHERE ref=?", (status, comment, ref))
        c.close()
        self.db.commit()

    def delete_file(self, path):
        c = self.db.cursor()
        c.execute("DELETE FROM files WHERE path=?", (path,))
        c.close()
        self.db.commit()
        
    def add_log(self, level, notes, dbtime=None):
        c = self.db.cursor()
        if dbtime is None:
            dbtime = "datetime('now', 'localtime')"
        else: 
            dbtime = "'{}'".format(dbtime)
        sql = "INSERT INTO log (stamp, severity, notes) VALUES ({}, ?, ?)".format(dbtime)
        c.execute(sql, (level, notes))
        c.close()
        self.db.commit()
        
    def get_log(self):
        c = self.db.cursor()
        c.execute("SELECT stamp, severity, notes FROM log ORDER BY stamp DESC LIMIT 100")
        r = c.fetchall()
        c.close()
        return r
    
    def trim_log(self):
        c = self.db.cursor()
        c.execute("DELETE FROM log WHERE stamp < date('now','-1 months')")
        c.execute("DELETE FROM sent_files WHERE stamp < date('now','-1 months')")
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


MAP_LEVELS={logging.DEBUG: 0, logging.INFO: 0, logging.ERROR: 1, logging.WARN: 1, logging.CRITICAL: 2, logging.FATAL: 2}

class SQLiteHandler(logging.Handler):
    """
    Logging handler for SQLite.
    Based on Vinay Sajip's DBHandler class (http://www.red-dove.com/python_logging.html)
                   VALUES (
                        '%(dbtime)s',
                        '%(name)s',
                        %(levelno)d,
                        '%(levelname)s',
                        '%(msg)s',
                        '%(args)s',
                        '%(module)s',
                        '%(funcName)s',
                        %(lineno)d,
                        '%(exc_text)s',
                        %(process)d,
                        '%(thread)s',
                        '%(threadName)s'
                   );
                   """

    
    def __init__(self, db):
        logging.Handler.__init__(self)
        self.db = db

    def formatDBTime(self, record):
        record.dbtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))

    def emit(self, record):
       
        # Use default formatting:
        self.format(record)
        # Set the database time up:
        self.formatDBTime(record)
        level = MAP_LEVELS.get(record.levelno, 0)
        notes = "{} {}({}):{}".format(record.msg,record.module, record.funcName, record.lineno)
        if record.exc_info:
            notes += " "+logging._defaultFormatter.formatException(record.exc_info)
        # Insert log record:
        self.db.add_log(level, notes, dbtime=record.dbtime)