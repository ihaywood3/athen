import imaplib, select, os, email, time, logging

import base

IMAP_HOST = 'localhost'
#IMAP_HOST='athen.email'
WAIT_TIME=900

class IMAP4_SSL_IDLE(imaplib.IMAP4_SSL):
    def idle(self):
        tag = self._new_tag()
        self.send("%s IDLE\r\n" % tag)
        response = self.readline()
        self.loop = True
        if response == '+ idling\r\n':
            return
        else:
            raise base.PermanentError("IDLE not handled? : %s" % response)
    
    def idle_read(self):
            resp = self.readline()
            return resp[2:-2].split(' ')

    def done(self):
        self.send("DONE\r\n")
        self.loop = False
        
class Emailer:
    
    def wait(self,timeout):
        time.sleep(timeout)
    
    def __init__(self,db):
        self.db = db
        self.fails = 0
        self.running = True
        self.conn = None
        
    def loop(self):
        while self.running:
            self.run()
            
    def run(self):
        cfg = self.db.get_all_configs()
        logging.debug("configs: {}".format(repr(cfg)))
        try:
            if cfg.get('username','') == '':
                raise base.PermanentError("no login information")
            if self.conn is None:
                self.conn = IMAP4_SSL_IDLE(cfg.get('host',IMAP_HOST))
                self.conn.debug = 4
                typ, data = self.conn.login(cfg['username'],cfg['password'])
                if typ != "OK": raise base.PermanentError("Cannot log in {} {}".format(typ, repr(data)))
                typ, data = self.conn.select("INBOX")
                if typ != "OK": raise base.PermanentError("Cannot select INBOX {} {}".format(typ, repr(data)))
            typ, data = self.conn.search(None, "ALL")
            if typ == "OK":
                for num in data[0].split():
                    rv, data = self.conn.fetch(num, '(RFC822)')
                    if rv != 'OK':
                        raise base.PermanentError("error getting message {} {} {}".format(num,rv,repr(data)))
                    msg = email.message_from_string(data[0][1])
                    s='Message {}: {} {}'.format(num, msg["From"], msg['Subject'])
                    logging.debug(s)
            else:
                logging.info("No messages found")
            self.fails = 0
            cont = True
            while cont and self.running:
                logging.debug("entering IDLE")
                self.conn.idle()
                reps = cfg.get('timeout',WAIT_TIME)/5
                fd = self.conn.socket().fileno()
                i = 0
                while i < reps and cont and self.running:
                    try: 
                        logging.debug("select()")
                        rlist, wlist, xlist = select.select([fd],[],[fd],5)
                    except select.error as err:
                        if err.args[0] == 4: # interrupted by signal
                            logging.debug("select() broken by signal")
                            cont = False
                        else:
                            raise
                    if fd in rlist:
                        logging.debug("data ready on fd")
                        resp = self.conn.idle_read()
                        cont = False
                    if fd in xlist:
                        raise base.TempError("error condition on select()")
                    self.wait(0.1)
                logging.debug("IDLE DONE")
                self.conn.done()
        except base.PermanentError as err:
            logging.exception("permanent error, pausing until reconfig")
            new_cfg_time = old_cfg_time = cfg.get('config_time','UNKNOWN')
            while new_cfg_time == old_cfg_time and self.running:
                logging.debug("checking if config has changed")
                self.wait(cfg.get('timeout',WAIT_TIME))
                new_cfg_time = (self.db.get_config('config_time') or "UNKNOWN")
        except:
            logging.exception("some other error")
            self.conn = None
            if self.fails > 5:
                logging.critical("too many fails, exiting")
                self.running = False
            else:
                self.wait(10)
                self.fails = self.fails+1
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                