import imaplib, select, os, os.path, glob, email, time, logging, sys, shutil, pudb, threading, ConfigParser, socket, re
import email.mime.text
import email.message
import email.mime.multipart
import email.mime.nonmultipart
import email.mime.message
import email.mime.base
import email.encoders
import email.utils
import smtplib
#import docx

import base, rtf, sys
sys.path.append('../lib')
import pit




IMAP_HOST = 'localhost'
#IMAP_HOST='athen.email'
WAIT_TIME=900

# message statues
STATUS_DELIVERED=0
STATUS_PENDING=1
STATUS_FAILED=2

# Emailer modes
MODE_RUNNING=0
MODE_IDLING=1
MODE_ERROR=2
MODE_QUIT=3

EMAIL_REGEXP=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

class IMAP4_SSL_IDLE(imaplib.IMAP4_SSL):
    def idle(self):
        tag = self._new_tag()
        self.send("%s IDLE\r\n" % tag)
        while True:
            resp = self.readline()
            logging.debug("line after IDLE %r" % resp)
            if resp == '+ idling\r\n':
                return
            elif resp[0:1] == "* ": # a status message, ignore it here
                continue
            else:
                raise base.PermanentError("IDLE not handled? : %s" % resp)

    def done(self):
        self.send("DONE\r\n")
        # we don't handle return values here as subsequent commands will 
        # bit of a hack as we are not picking up errors.

class QuitException(Exception): pass

class Emailer:
    
    def wait(self,timeout=None):
        if self.cfg['debug']: sys.exit()
        self.check_mode()
        self.event.clear()
        self.event.wait(timeout)
        self.check_mode()
        
    def _set_daemon_pid(self,pid):
        """Overridable way of setting PID"""
        self.db.set_config('daemon_pid',pid)
        
    
    def __init__(self,config):
        """config is a dictionary of config values
        """
        self.cfg = config
        if not 'debug' in config: config['debug'] = False
        self.db = base.DB(config['dbfile'],config['debug'])
        self.fails = 0
        self.conn = None
        self.hWaitStop = None # help Windows version
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.mode = MODE_RUNNING
        self.config_dirty = True
        self.thread = None
        self.created_downloaded_folder = False
        self.created_errors_folder = False
        self.downloaded_files = []
        self.uploaded_files = []
        
    def check_mode(self):
        with self.lock:
            if self.mode == MODE_QUIT:
                raise QuitException
            
    def set_external_quit(self):
        """
        another thread wants to tell this one to quit
        """
        with self.lock:
            if self.mode == MODE_QUIT:
                return
            elif self.mode == MODE_RUNNING:
                # politely "ask" the thread to quit
                self.mode = MODE_QUIT
                return
            elif self.mode == MODE_ERROR:
                self.event.set() # wake up the waiter
                return
            if self.mode == MODE_IDLING:
                self.mode = MODE_QUIT
                # this will break the select() as the server will reply to DONE
                self.sock.done()
                
    def set_external_reconfigure(self,new_cfg):
        """tell the thread we have reloaded the configuration
        """
        self.cfg = new_cfg
        self.config_dirty = True
        self.event.set()

    def __call__(self):
        self.loop()

    def loop_thread(self):
        self.thread = threading.Thread(target=self.loop)
        self.thread.start()

    def loop(self):
        logging.debug("configs: {}".format(repr(self.cfg)))
        while True: # we use QuitException or other error to escape
            try:
                self.check_mode()
                if self.config_dirty:
                    # config is already loaded
                    self.config_dirty = False
                if self.cfg.get('username','') == '':
                    raise base.PermanentError("no login information")
                if not 'download_path' in self.cfg:
                    raise base.PermanentError("no download path set")
                if not os.access(self.cfg['download_path'],os.W_OK):
                    raise base.PermanentError("I don't have write access to {}".format(self.cfg['download_path']))
                if self.conn is None:
                    self.conn = IMAP4_SSL_IDLE(self.cfg.get('host',IMAP_HOST))
                    self.hSocketEvent = None  # for Windows client, unusued on UNIX
                    self.conn.debug = 4
                    typ, data = self.conn.login(self.cfg['username'],self.cfg['password'])
                    logging.debug("IMAP login %r %r" % (typ, data))
                    if typ != "OK": raise base.PermanentError("Cannot log in {} {}".format(typ, repr(data)))
                    typ, data = self.conn.select("INBOX")
                    logging.debug("selected INBOX %r %r" % (typ, data))
                    if typ != "OK": raise base.PermanentError("Cannot select INBOX {} {}".format(typ, repr(data)))
                self.check_mode()
                while True:
                    typ, data = self.conn.search(None, "ALL")
                    logging.debug("IMAP search %r %r" % (typ, data))
                    self.check_mode()
                    if typ == "OK":
                        all_msgs = data[0].split()
                        if len(all_msgs) == 0: break
                        for num in all_msgs:
                            rv, data = self.conn.fetch(num, '(RFC822)')
                            if rv != 'OK':
                                logging.panic("error getting message {} {} {}".format(num,rv,repr(data)))
                            else:
                                msg = email.parse_message_from_string(data[0][1])
                                self.handle_email(msg,num)
                            self.check_mode()
                    else:
                        break # no messages, so move on
                self.fails = 0
                # TODO: self.uploaded_files = self.db.get_uploads_status() # grab so the GUI client can get it
                # scan directories for upload
                self.scan_directories()
                self.check_consumed_files()
                try:
                    with self.lock:
                        if self.mode == MODE_QUIT:
                            raise QuitException
                        self.mode = MODE_IDLING
                        self.conn.idle()
                    self.wait_socket(self.conn.socket(),self.cfg.get('timeout',WAIT_TIME))
                finally:
                    with self.lock:
                        if self.mode == MODE_QUIT:
                            raise QuitException
                        self.mode = MODE_RUNNING
                        self.conn.done()
            except base.PermanentError as err:
                logging.exception("permanent config error, pausing until reconfig")
                self.mode = MODE_ERROR
                self.wait() # external thread will wake us up when config changed
            except QuitException:
                try:
                    self.conn.close()
                    self.conn.logout()
                except:
                    log.exception("while closing connection")
                # re-raise to escape the loop. this hte only exception
                # that gets re-raised, and so only way to escape the loop
                raise
            except imaplib.IMAP4.error as err:
                if err.args == ('[AUTHENTICATIONFAILED] Authentication failed.',):
                    logging.error("Authentication failed")
                    try:
                        self.conn.logout()
                    except: pass
                    self.conn = None
                    self.mode = MODE_ERROR
                    self.wait()
                else:
                    logging.exception("other IMAP error")
                    self.temp_error()
            except socket.gaierror as err:
                logging.error("DNS lookup failed or similar %r" % err)
                self.conn = None
                time.sleep(60)
                # so repeat forever waiting for DNS/internet to return
            except socket.error as err:
                if err.errno == 110:
                    logging.error("connection timed out")
                    # connection timed out
                    self.conn = None
                    time.sleep(60)
                    # so repeat forever waiting for Internet to return
                else:
                    logging.error("some other socket error: %d %r" % (err.errno,err))
                    self.temp_error()
            except:
                logging.exception("some other error")
                self.temp_error()
                
    def temp_error(self):
        with self.lock:
            try:
                self.conn.close()
            except: pass
            try:
                self.conn.logout()
            except: pass
            if self.mode == MODE_QUIT: raise QuitException
            self.mode = MODE_ERROR
            self.conn = None
        if self.fails > 5:
            logging.critical("too many fails, pausing until reconfig")
            self.wait() # external thread will wake us up when reconfigured
        else:
            # wait 10 seconds and try again
            self.wait(10)
            self.fails = self.fails+1
    
    def wait_socket(self,sock,timeout):
        # UNIX version defined here, we might do different on Windows
        fd = sock.fileno()
        read_fd = False
        try: 
            logging.debug("select()")
            rlist, wlist, xlist = select.select([fd],[],[fd],timeout)
            if fd in rlist:
                read_fd = True
            if fd in xlist:
                raise base.TempError("error condition on select()")
        except select.error as err:
            if err.args[0] == 4: # interrupted by signal
                logging.debug("select() broken by signal")
                # the signal handler will have set flags for what we need to do
            else:
                raise
        return read_fd

                
    def handle_email(self,msg,num):
        try:
            if not "Message-ID" in msg:
                raise Exception("no Message-ID","")
            if not self.handle_parts(msg,msg):
                raise Exception("no valid MIME component found")
            if not self.created_downloaded_folder:
                self.conn.create("Downloaded") # ignore result as harmless error if exists
                self.created_downloaded_folder = True
            typ, data = self.conn.copy([num],"Downloaded")
            if typ != "OK":
                logging.panic("copy of %r %r to Downloaded failed" % (num, data))
            else:
                typ, data = self.conn.store([num],"+FLAGS","\\Deleted")
                if typ != "OK":
                    logging.panic("delete of % failed (%r)" % (num, data))
                else:
                    logging.debug("deleting message %r %r" % (num,typ))
        except:
            logging.exception("failure in saving message")
            typ, val, tb = sys.exc_info()
            txt = "{}\r\n{}\r\n".format(str(val),str(tb))
            if not self.created_errors_folder:
                self.conn.create("Error") # ignore the result, harmless error if it exists
                self.created_errors_folder = True
            typ, data = self.conn.copy([num],"Error")
            if typ != "OK":
                logging.panic("copy of %r %r to Errors failed" % (num, data))
            else:
                typ, data = self.conn.store([num],"+FLAGS","\\Deleted")
                if typ != "OK":
                    logging.panic("delete of % failed (%r)" % (num, data))
                else:
                    logging.debug("deleting message %r %r" % (num,typ))        
            self.send_dsn_report(msg,txt,status="5.6.0",diagnostic=str(val))
            
            
    def handle_parts(self,msg,inner):
        for part in inner.walk():
            if part.get_content_type() == "multipart/encrypted":
                data = part.get_payload(0)
                pgp_obj = part.get_payload(1)
                if pgp_obj.get_content_type() != "application/pgp-encrypted":
                    logging.warning("pgp-encrypted packet not found")
                data = data.get_payload(decode=True)
                # TODO: data = self.decrypt_message(data)
                decrypted = email.message_from_string(data)
                return self.handle_parts(msg,decrypted)
            if part.get_content_type() == "message/delivery-status":
                orig_id = part.get_payload(0)["Original-Envelope-Id"]
                ostatus = STATUS_FAILED
                action = part.get_payload(1)["Action"].strip().lower()
                status = part.get_payload(1)["Status"]
                status2 = status.split('.')
                diag = part.get_payload(1).get("Diagnostic-Code",None)
                comment = []
                logging.info("Got DSN: {} {} {}".format(orig_id,action,status))
                if action == 'delivered' and status2[0] == "2":
                    ostatus = STATUS_DELIVERED
                elif action == 'delayed':
                    ostatus = STATUS_PENDING
                elif action <> 'failed':
                    comment.append("Action: {}".format(action))
                if diag is None and status2[0] != "2":
                    comment.append("Status code: {}".format(status))
                    ostatus = STATUS_FAILED
                if diag:
                    diag2 = diag.split(';',2)
                    if len(diag2) == 1:
                        comment.append(diag)
                    else:
                        comment.append(diag2[1])
                comment = " ".join(comment)
                self.db.set_file_status(orig_id,ostatus,comment)
                return True
            if part.get_content_type() == 'message/disposition-notification':
                part = part.get_payload(0)
                comment = disp = part["Disposition"]
                ostatus = STATUS_FAILED
                orig_id = part["Original-Message-Id"]
                logging.info("Got read receipt: {} {}".format(orig_id,disp))
                try:
                    if disp.split(';')[1].strip().lower().startswith("displayed"):
                        ostatus = STATUS_DELIVERED
                        comment = ""
                except: pass
                self.db.set_file_status(orig_id,ostatus,comment)
                return True
            # multipart/* are just containers
            if part.get_content_maintype() == 'multipart':
                logging.debug("skipping {} as multipart".format(part.get_content_type()))
                continue
            if not 'Content-Disposition' in part:
                logging.debug("{} skipping as no Content-Disposition".format(part.get_content_type()))
                continue
            if not part['Content-Disposition'].startswith("attachment"):
                logging.debug("skipping {} as Content-Disposition not attachment".format(part.get_content_type()))
                continue
            data = part.get_payload(decode=True)
            if data[:4] != "001 ":
                msg = "file beginning with {!r} doesn't look like PIT, rejecting".format(data[:10])
                logging.warning(msg)
                raise Exception(msg)
            filename = self.db.get_ref_number()+'.PIT'
            fullpath = os.path.join(self.cfg['download_path'], filename)
            logging.info("writing out to {}".format(fullpath))
            with open(fullpath, 'wb') as f:
                f.write(data)
            self.db.add_file(filename, msg["From"], msg["Message-ID"])
            self.send_dsn_report(msg,"The file has been received and saved to disc on the remote system, but it has not yet been processed",action="delayed",diagnostic="saved to disc")
            return True
        # we got to end without handling the message
        return False
            
    def send_dsn_report(self,orig_msg=None,txt_report="",action="delivered",status="2.0.0",diagnostic=None,dest=None,msg_id=None):
        if orig_msg and "Auto-Submitted" in orig_msg:
            logging.warn("trying to send DSN on an autosubmitted message {}".format(orig_msg["Message-Id"]))
            return
        reply = email.mime.multipart.MIMEMultipart(_subtype="report",report_type="delivery-notification")
        if orig_msg:
            reply['From'] = orig_msg.get("Delivered-To",orig_msg.get("To"))
            reply["To"] = orig_msg["From"]
            reply["References"] = orig_msg["Message-Id"]
        else:
            reply["From"] = self.cfg['username']+"@"+IMAP_HOST
            reply["To"] = dest
            reply["References"] = msg_id
        domain = email.utils.parseaddr(reply["From"])[1]
        if "error_email" in self.cfg:
            reply["Reply-To"] = self.cfg["error_email"]
        if status == "2.0.0":
            reply["Subject"] = "Successful Mail Delivery Report"
        else:
            reply["Subject"] = "[ATHEN] MESSAGE DELIVERY ERROR"
        reply["Auto-Submitted"] = "auto-replied"
        reply["Message-Id"] = email.utils.make_msgid(domain)
        # now the first component: human-readable report
        reply_text = email.mime.text.MIMEText(_text=txt_report)
        reply.attach(reply_text)
        # second component: machine-readable
        # make action sane
        if status != "2.0.0" and action == "delivered":
            action = "failed"
        # do structured report
        sr1 = email.message.Message()
        sr1["Reporting-MTA"] = "rfc822; "+domain
        sr1["Original-Envelope-Id"] = reply["References"]
        sr1["Arrival-Date"] = email.utils.formatdate()
        sr2 = email.message.Message()
        sr2["Final-Recipient"] = "rfc822; "+domain
        sr2["Action"] = action
        sr2["Status"] = status
        if diagnostic:
            sr2["Diagnostic-Code"] = "X-Athen; "+diagnostic
        part2 = email.mime.message.MIMEMessage(sr1,_subtype='delivery-status')
        # HACK: add a part when we are not 'supposed' to
        email.message.Message.attach(part2,sr2)
        reply.attach(part2)
        if action == "failed" and orig_msg:
            # part 3: the headers of the original message
            hdrs = "".join("{}: {}\r\n".format(k, orig_msg[k]) for k in orig_msg.keys())
            part3 = email.mime.text.MIMEText(_text=hdrs,_subtype="rfc822-headers")
            reply.attach(part3)
        logging.debug("sending DSN to %s with code %r message %r" % (dest,status,diagnostic))
        self.send_email(reply)
        
    def send_email(self, themail):
        s = smtplib.SMTP(IMAP_HOST,587)
        s.starttls()
        s.login(self.cfg['username'],self.cfg['password'])
        themail_str = themail.as_string()
        logging.debug(themail_str)
        s.sendmail(themail['From'], [themail['To']], themail_str)
        s.quit()
    
    def split_paths(self, path):
        """split a list of paths into parts
        So Windows client can override and use ; instead"""
        return path.split(':')
    
    def scan_directories(self):
        upload_path = self.cfg.get('upload_path',None)
        if upload_path is None:
            logging.info("No upload path set so no uploading")
            return
        errors_path = self.cfg.get('errors_path',None)
        if errors_path is None:
            logging.error("No error path set so no uploading")
            return
        waiting_path = self.cfg.get('waiting_path',None)
        if waiting_path is None:
            logging.error("Can't upload as no waiting_path (uploads awaiting confirmation)")
            return
        dirs = self.split_paths(upload_path)
        for d in dirs:
            if os.access(d,os.X_OK|os.R_OK|os.W_OK):
                exts = self.cfg.get('extensions','*.rtf,*.pit')
                for ext in exts.split(','):
                    for fn in glob.glob(os.path.join(d,ext)):
                        if os.access(fn,os.R_OK|os.W_OK):
                            try:
                                if ext == "*.rtf":
                                    data = rtf.parse_rtf(fn)
                                    pitfile = pit.make(data)
                                    assert re.match(EMAIL_REGEXP,data['recipient_email'])
                                    self.send_as_pit(pitfile,fn,data['recipient_email'])
                                if ext == "*.pit":
                                    with open(fn,"r") as fd:
                                        pitfile = fd.read()
                                    recip = pit.extract_addressee(pitfile)
                                    assert recip
                                    #assert re.match(EMAIL_REGEXP,recip) 
                                    self.send_as_pit(pitfile,fn,recip)
                            except:
                                logging.exception("problem sending {}".format(fn))
                                shutil.move(fn,errors_path)
                        else:
                            logging.warn("path {} would match but I don't have access".format(fn))
                    self.check_mode()
            else:
                logging.warn("directory {} in upload list but I don't have access".format(d))
    
    def send_as_pit(self,pitfile,original_filename,recipient_email):
        pudb.set_trace()
        mail = email.mime.application.MIMEApplication(pitfile,_subtype="x-pit")
        mail["To"] = recipient_email
        mail["From"] = self.cfg["username"]+"@"+IMAP_HOST
        mail["Subject"] = "ATHEN message as PIT"
        mail["X-Athen-Original-Filename"] = os.path.basename(original_filename)
        mail["Message-Id"] = msg_id = email.utils.make_msgid(IMAP_HOST)
        mail["Content-Disposition"] = "attachment"
        mail['X-Athen-Security'] = 'secure'
        mail['User-Agent'] = 'ATHEN/0.1'
        self.send_email(mail)
        shutil.move(original_filename,self.cfg['waiting_path'])
        self.db.add_sent_file(os.path.basename(original_filename),recipient_email,msg_id)        
    
    def check_consumed_files(self):
        dl_path = self.cfg.get('download_path',None)
        if not os.path.exists(dl_path):
            raise base.PermanentError("download path {} does not exist".format(dl_path))
        self.downloaded_files = self.db.get_files() # hold this in RAM as GUI client may want to look (and can't use DB as wrong thread)
        for fn in self.downloaded_files:
            fullpath = os.path.join(dl_path,fn['path'])
            if not os.path.exists(fullpath):
                # the file no longer exists: we assume the downstream EMR has eaten it
                # No, this isn't a particularly good way of "confirming" delivery,
                # but it's the best we've got.
                self.db.delete_file(fn['path'])
                self.send_dsn_report(dest=fn['origin'],msg_id=fn['ref'],diagnostic="remote file read by EMR",
                                     txt_report="""The file has been saved to disc, 
                                    and then deleted, which we assume means it has 
                                    been read by the receipient's medical record system""")
            self.check_mode()
                
                
                
                
                
                
                
                
                
                