#! /bin/env python3

"""
"Message accounting": tracking incoming and outgoing messages
and return/delivery receipts
"""

import os, os.path, sys
from email.utils import make_msgid
import logging
logger = logging.getLogger(__name__)

import util, userdb, config


def guarantee_msgid(msg):
    if not "Message-Id" in msg:
        msg['Message-Id'] = make_msgid(domain=config.domain)
    return msg['Message-Id']

def sent_filter(msg):
    """the outgoing accounting filter
    currently just does a log of the message transit and returns msg unaltered"""
    udb = userdb.UserDB()
    udb.update_messages(guarantee_msgid(msg),"SENT",outgoing=True,temail=msg['To'],subject=msg.get('Subject',"NO SUBJECT"))
    return msg

def received_filter(msg):
    """
    the incoming filter for accounting/acknowleding
    returns filtered message, possibly changed
    CAN EVEN RETURN None: means this filter has "eaten" a
      delivery/tracking message and recorded its import
    in the log for the message of which it is an acknowledgment)
    """
    global logger
    udb = userdb.UserDB()
    ostatus = "FAILED"
    has_dsn = False
    for part in msg.walk():
        if part.get_content_type() == "message/delivery-status":
            has_dsn = True
            orig_id = part.get_payload(0)["Original-Envelope-Id"]
            udb.flush_with_id(orig_id)
            logger.debug("Processing delivery status orig_id '{}'".format(orig_id))
            try:
                action = part.get_payload(1)["Action"].strip().lower()
                logger.debug("Action: '{}'".format(action))
                if action == 'delayed' or action == 'relayed' or action == 'expanded':
                    ostatus = "PENDING"
                status = part.get_payload(1)["Status"]
                logger.debug("Status: '{}'".format(status))
                status2 = status.split('.')
                if status2[0] == "2":
                    logger.info("Email analysed as successful delivery")
                    logger.info("Action was '{}'".format(action))
                    if ostatus != 'PENDING': ostatus = "OK"
                diag = part.get_payload(1).get("Diagnostic-Code",None)
                if diag is None:
                    if ostatus == "FAILED":
                        logging.warning("Delivery failed with status code: {}".format(status))
                else:
                    logging.debug("Diagnostic-Code: '{}'".format(diag))
                    diag = diag.strip().split(';',2)
                    if len(diag) == 2:
                        diag = diag[1].strip()
                    if ostatus == "FAILED":
                        logging.warning("Delivery failed with '{}'".format(diag))
            except:
                logging.exception("Parsing delivery notification")
            udb.update_messages(orig_id,ostatus)
        if part.get_content_type() == 'message/disposition-notification':
            has_dsn = True
            part = part.get_payload(0)
            orig_id = part["Original-Message-Id"]
            udb.flush_with_id(orig_id)
            try:
                comment = disp = part["Disposition"]
                logger.debug("Got read receipt raw Disposition: '{}' orig_id '{}'".format(disp,orig_id))
                try:
                    if disp.split(';')[1].strip().lower().startswith("displayed"):
                        logger.info("Received read-receipt")
                        ostatus = "OK"
                except: pass
            except:
                logger.exception("Parsing read receipt")
            udb.update_messages(orig_id,ostatus)
    if not has_dsn:
        udb.update_messages(guarantee_msgid(msg),"OK",outgoing=False,temail=msg['From'],subject=msg['Subject'])
        logger.info("incoming message logged")
    if not has_dsn or ostatus == "FAILED":
        return (None, "INBOX", msg)
    else:
        return (None, None, None)
