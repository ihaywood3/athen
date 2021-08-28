"""
Creating E-mail Delivery Status Notifcation
"""

import email.mime.multipart
import email.utils

def prepare_dsn_report(self,orig_msg=None,txt_report="",action="delivered",status="2.0.0",diagnostic=None,dest=None,msg_id=None):
    logger = logging.getLogger("userdb")
    if orig_msg and "Auto-Submitted" in orig_msg:
        logger.error("trying to send DSN on an autosubmitted message {}".format(orig_msg["Message-Id"]))
        return
    reply = email.mime.multipart.MIMEMultipart(_subtype="report",report_type="delivery-notification")
    if not orig_msg is None:
        if not "To" in orig_msg:
            logging.critical("can't send DSN as original message so broken as no To field")
            return None
        reply['From'] = orig_msg.get("Delivered-To",orig_msg.get("To"))
        if not "From" in orig_msg:
            logging.critical("can't send DSN as original message so broken as no From field")
            return None
        reply["To"] = dest = orig_msg["From"]
        if not "Message-Id" in orig_msg:
            logging.critical("can't send DSN as original message so broken as no Message-Id field")
            return None
        reply["References"] = orig_msg["Message-Id"]
    else:
        assert dest
        assert msg_id
        reply["From"] = "{} <{}@{}>".format(os.environ["REALNAME"],os.environ["USER"],config.domain)
        reply["To"] = dest
        reply["References"] = msg_id
    # make action sane
    if status != "2.0.0" and action == "delivered":
        action = "failed"
    # set subject
    subj = ""
    if status == "2.0.0":
        if action=="delivered":
            subj = "[ATHEN] Successful Mail Delivery" 
        elif action=="delayed" or action=="relayed":
            subj = "[ATHEN] Mail in transit"
        else:
            logger.critical("UNKNOWN action \"{}\" with status 2.0.0. SHOULD NEVER HAPPEN".format(action))
            subj = "[ATHEN] MESSAGE DELIVERY ERROR"
    else:
        subj = "[ATHEN] MESSAGE DELIVERY ERROR"
    if orig_msg and "Subject" in orig_msg:
        subj = subj+": "+orig_msg["Subject"]
    reply["Subject"] = subj
    reply["Auto-Submitted"] = "auto-replied"
    reply["Message-Id"] = email.utils.make_msgid(domain=config.domain)
    # now the first component: human-readable report
    if not txt_report:
        if action == "delivered":
            txt_report = "Message delivered successfully"
        elif action == "delayed" or action == "relayed":
            txt_report = "Message in transit"
        else:
            txt_report = "Message delivery failed "+(diagnostic or "")
    reply_text = email.mime.text.MIMEText(_text=txt_report)
    reply.attach(reply_text)
    # second component: machine-readable
    # do structured report
    sr1 = email.message.Message()
    sr1["Reporting-MTA"] = "dns; "+config.domain
    sr1["Original-Envelope-Id"] = reply["References"]
    sr1["Arrival-Date"] = email.utils.formatdate()
    sr2 = email.message.Message()
    sr2["Final-Recipient"] = "rfc822; "+os.environ["USER"]+"@"+config.domain
    sr2["Original-Recipient"] = "rfc822; "+os.environ["USER"]+"@"+config.domain
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
        hdrs = "".join("{}: {}\r\n".format(k, orig_msg[k]) for k in list(orig_msg.keys()))
        part3 = email.mime.text.MIMEText(_text=hdrs,_subtype="rfc822-headers")
        reply.attach(part3)
    logger.info("sending DSN to %s with code %r message %r" % (dest,status,diagnostic))
    return reply
