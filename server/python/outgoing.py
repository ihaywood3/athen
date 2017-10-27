"""The outgoing mail filter"""

import os, sys, os.path, email, smtplib, subprocess, email.generator, logging, email.utils
import gpg, pgp_mime

if os.path.exists("/home/ian/athen/lib"):
    sys.path.append("/home/ian/athen/lib")
else:
    sys.path.append("/usr/local/lib/athen/lib")

import util, dsn, pit, myldap, config, mailfilter # these modules shared between the client and server
import accounting, deliver, userdb

uctx, msg = deliver.startup()
try:
    if not "Message-Id" in msg:
        msg["Message-Id"] = email.utils.make_msgid(domain=config.domain)
    auto = False
    if not auto:
        for part in msg.walk():
            if part.get_content_type() in ["message/delivery-status","message/disposition-notification"]:
                auto = True
                orig_id = part.get_payload(0)["Original-Envelope-Id"]
    if not auto and "Auto-Submitted" in msg:
        auto = True
        orig_id = None
    udb = userdb.UserDB()
    if auto:
        if orig_id:
            udb.flush_with_id(orig_id)
            logging.info("sent confirmation email")
        deliver.postfix_deliver(msg,want_dsn=False)
    else:
        # forcibly add a dispositon notfiication if the mail client hasn't done it
        if not "Dispositon-Notification-To" in msg:
            if "Reply-To" in msg:
                msg["Disposition-Notification-To"] = msg["Reply-To"]
            else:
                msg["Disposition-Notification-To"] = msg["From"]
        msg = accounting.sent_filter(msg)
        # FIXME: do outgoing PGP/MIME here
        deliver.postfix_deliver(msg,want_dsn=True)
        logging.info("sent mail")
        logging.debug("sent mail from '{}' to '{}' subject '{}' id '{}'".format(msg['From'],msg['To'],msg['Subject'],msg['Message-Id']))
    
except:
    logging.exception("outgoing failed")
    raise
