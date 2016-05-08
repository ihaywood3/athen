import imaplib, select, os, email, time, logging, sys
import email.mime.text
import email.mime.multipart
import email.mime.message
import email.mime.base
import email.encoders
import email.utils

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
        self.db.set_config('daemon_pid',os.getpid())
        self.fails = 0
        self.running = True
        self.conn = None
        
    def loop(self):
        try:
            while self.running:
                self.cfg = cfg = self.db.get_all_configs()
                logging.debug("configs: {}".format(repr(cfg)))
                if cfg.get('username','') == '':
                    raise base.PermanentError("no login information")
                if not 'download_path' in cfg:
                    raise base.PermanentError("no download path set")
                if not os.access(cfg['download_path'],os.W_OK):
                    raise base.PermanentError("I don't have write access to {}".format(cfg['download_path']))
                if self.conn is None:
                    self.conn = IMAP4_SSL_IDLE(cfg.get('host',IMAP_HOST))
                    self.hSocketEvent = None  # for Windows client, unusued on UNIX
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
                            logging.c("error getting message {} {} {}".format(num,rv,repr(data)))
                        msg = email.message_from_string(data[0][1])
                        self.handle_msg(msg)
                else:
                    logging.info("No messages found")
                self.fails = 0
                # scan directories for upload
                
                cont = True
                while cont and self.running:
                    logging.debug("entering IDLE")
                    self.conn.idle()
                    cont, read_fd = self.wait_socket(self.conn.socket(),cfg.get('timeout',WAIT_TIME))
                    if read_fd:
                        logging.debug("data ready on fd")
                        resp = self.conn.idle_read()
                        cont = False
                logging.debug("IDLE DONE")
                self.conn.done()
            self.conn.close()
            self.conn.logout()
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
    
    def wait_socket(self,sock,timeout):
        # UNIX version defined here
        fd = sock.fileno()
        read_fd = False
        cont = True
        try: 
            logging.debug("select()")
            rlist, wlist, xlist = select.select([fd],[],[fd],timeout)
        except select.error as err:
            if err.args[0] == 4: # interrupted by signal
                logging.debug("select() broken by signal")
                cont = False
            else:
                raise
        if fd in rlist:
            read_fd = True
        if fd in xlist:
            raise base.TempError("error condition on select()")
        return (cont, read_fd)

                
    def handle_email(self,download_path,msg):
        try:
            if not "Message-ID" in msg:
                raise Exception("no Message-ID","")
            if not self.handle_parts(download_path,msg,msg):
                raise Exception("no valid MIME component found")
        except:
            logging.exception("failure in saving message")
            typ, val, tb = sys.exc_info()
            txt = "{}\r\n{}\r\n".format(str(val),str(tb))
            self.send_dsn_report(msg,txt,status="5.6.0",diagnostic=str(val))
            
    def handle_parts(self,download_path,msg,inner):
        for part in inner.walk():
            # multipart/* are just containers
            # if encrypted
            #  return self.handle_parts(download_path,msg,decrypted)
            # if dsn/msn itself
            # handle_dsn
            # return True
            if part.get_content_maintype() == 'multipart':
                logging.debug("skipping {} as multipart".format(part.get_content_type()))
                continue
            if not 'Content-Disposition' in part:
                logging.debug("{} skipping as no Content-Disposition".format(part.get_content_type()))
                continue
            if not part['Content-Disposition'].startswith("attachment"):
                logging.debug("skipping {} as Content-Disposition not attachment".format(part.get_content_type()))
                continue
            filename = part.get_filename()
            data = part.get_payload(decode=True)
            if not filename:
                filename = self.create_name(data)
            if db.check_file(filename):
                filename = self.create_name(data)
            with open(os.path.join(download_path, filename), 'wb') as f:
                f.write(data)
            self.db.add_file(filename, msg["From"], msg["Message-ID"])
            logging.info("saving attachment {} to {}".format(filename,download_path))
            return True
        # we got to end without handling the message
        return False
            
    def send_dsn_report(self,orig_msg,txt_report,status="2.0.0",diagnostic=None):
        reply = email.mime.multipart.MIMEMultipart(_subtype="report",_params={"report-type":"delivery-notification"})
        reply['From'] = orig_msg.get("Delivered-To",msg.get("To"))
        domain = email.utils.parseaddr(reply["From"])[1]
        if "error_email" in self.cfg:
            reply["Reply-To"] = self.cfg["error_email"]
        reply["To"] = orig_msg["From"]
        if status == "2.0.0":
            reply["Subject"] = "Successful Mail Delivery Report"
        else:
            reply["Subject"] = "[ATHEN] MESSAGE DELIVERY ERROR"
        reply["References"] = orig_msg["Message-Id"]
        reply["Auto-Submitted"] = "auto-replied"
        reply["Message-Id"] = email.utils.make_msgid(domain)
        # now the first component: human-readable report
        reply_text = email.mime.text.MIMEText(txt_report)
        email.encoders.encode_7or8bit(replay_text)
        reply.attach(reply_txt)
        # second component: machine-readable
        if status == "2.0.0":
            action = "delivered"
        else:
            action = "failed"
        structured_report = """Reporting-MTA: rfc822; {fro}\r
Original-Envelope-Id: {id}\r
Arrival-Date: {date}\r
\r
Final-Recipient: rfc822; {fro}\r
Action: {action}\r
Status: {status}\r
"""
        structured_report = structured_report.format(fro=domain,
                                id=orig_msg["Message-ID"],
                                date=email.utils.formatdate(),
                                action=action,status=status)
        if diagnostic:
            structured_report += "Diagnostic-Code: {}\r\n".format(diagnostic)
        part2 = email.mime.base.MIMEBase("message","delivery-status")
        part2.set_payload(structured_report)
        email.encoders.encode_7or8bit(part2)
        reply.attach(part2)
        if action == "failed":
            # part 3: the headers of the original message
            hdrs = "".join("{}: {}\r\n".format(k, orig_msg[k]) for k in orig_msg.keys())
            part3 = email.mime.text.MIMEText(_text=hdrs,_subtype="rfc822-headers")
            email.encoders.encode_7or8bit(part3)
            reply.attach(part3)
            
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                
                