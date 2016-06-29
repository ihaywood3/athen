import imaplib, select, os, os.path, glob, email, time, logging, sys, shutil, pdb
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

import base, rtf, pit



IMAP_HOST = 'localhost'
#IMAP_HOST='athen.email'
WAIT_TIME=900

STATUS_DELIVERED=0
STATUS_PENDING=1
STATUS_FAILED=2

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
        self.hWaitStop = None # help Windows version
        
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
                            logging.panic("error getting message {} {} {}".format(num,rv,repr(data)))
                        msg = email.message_from_string(data[0][1])
                        self.handle_email(msg)
                else:
                    logging.info("No messages found")
                self.fails = 0
                # scan directories for upload
                self.scan_directories()
                self.check_consumed_files()
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

                
    def handle_email(self,msg):
        try:
            if not "Message-ID" in msg:
                raise Exception("no Message-ID","")
            if not self.handle_parts(msg,msg):
                raise Exception("no valid MIME component found")
        except:
            logging.exception("failure in saving message")
            typ, val, tb = sys.exc_info()
            txt = "{}\r\n{}\r\n".format(str(val),str(tb))
            self.send_dsn_report(msg,txt,status="5.6.0",diagnostic=str(val))
            
    def handle_parts(self,msg,inner):
        for part in inner.walk():
            if part.get_content_type() == "multipart/encrypted":
                data = part.get_payload(0)
                pgp_obj = part.get_payload(1)
                if pgp_obj.get_content_type() != "application/pgp-encrypted":
                    logging.warning("pgp-encrypted packet not found")
                data = data.get_payload(decode=True)
                # data = self.decrypt_message(data)
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
            logging.error("Can't upload as no error_path set")
            return
        waiting_path = self.cfg.get('waiting_path',None)
        if waiting_path is None:
            logging.error("Can't upload as no waiting_path (uploads awaiting confirmation)")
            return
        dirs = self.split_paths(upload_path)
        for d in dirs:
            if os.access(d,os.X_OK|os.R_OK|os.W_OK):
                exts = self.cfg.get('extensions','*.rtf')
                for ext in exts.split(','):
                    for fn in glob.glob(os.path.join(d,ext)):
                        if os.access(fn,os.R_OK|os.W_OK):
                            if ext == "*.rtf":
                                try:
                                    data = rtf.parse_rtf(fn)
                                    pitfile = pit.make(data)
                                    mail = email.mime.application.MIMEApplication(pitfile,_subtype="x-pit")
                                    mail["To"] = data['recipient_email']
                                    mail["From"] = self.cfg["username"]="@"+IMAP_HOST
                                    mail["Subject"] = "ATHEN message as PIT"
                                    mail["X-Athen-Original-Filename"] = os.path.basename(fn)
                                    mail["Message-Id"] = msg_id = email.utils.make_msgid(IMAP_HOST)
                                    mail["Content-Disposition"] = "attachment"
                                    mail['X-Athen-Security'] = 'secure'
                                    mail['User-Agent'] = 'ATHEN/0.1'
                                    self.send_email(mail)
                                    shutil.move(fn,waiting_path)
                                    self.db.add_sent_file(os.path.basename(fn),data['recipient_email'],msg_id)
                                except:
                                    logging.exception("problem sending {}".format(fn))
                        else:
                            logging.warn("path {} would match but I don't have access".format(fn))
            else:
                logging.warn("directory {} in upload list but I don't have access".format(d))
                
    def check_consumed_files(self):
        dl_path = self.cfg.get('download_path',None)
        if not os.path.exists(dl_path):
            raise Exception("download path {} does not exist".format(dl_path))
        for fn in self.db.get_files():
            fullpath = os.path.join(dl_path,fn['path'])
            if not os.path.exists(fullpath):
                # the file no longer exists: we assume the downstream EMR has eaten it
                # No, this isn't a particularly good way of "confirming" delivery,
                # but it's the best we've got.
                self.db.delete_file(fn['path'])
                self.send_dsn_report(dest=fn['origin'],msg_id=fn['ref'],diagnostic="remote file read by EMR",txt_report="The file has been saved to disc, and then deleted, which we assume means it has been read by the receipient's medical record system")
                
                
                
                
                
                
                
                
                
                