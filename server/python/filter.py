#!/usr/bin/python

"""
this is the python filter script for outoging mail, called from
postfix.
At some future point may become a SMTP server in its own right
"""

import os, signal, sys, logging, email, re
logging.basicConfig(filename='/var/log/athen/filter.log')
import email.mime.text
import email.message
import email.mime.multipart
import email.mime.nonmultipart
import email.mime.message
import email.mime.base
import email.encoders
import email.utils

if os.path.exists("/home/ian/athen/lib"):
    sys.path.append("/home/ian/athen/lib")
else:
    sys.path.append("/usr/lib/athen/lib")

import util, pit # these modules shared between the client and server

HIGHSEC_SERVER='/var/spool/postfix/public/secure:-1'
LOWSEC_SERVER='localhost:25'

msg = email.message_from_file(sys.stdin)

sender = sys.argv[1]
recipient = sys.argv[2]
recipient_name, receipient_email = email.utils.parseaddr(receipient)


subject_re = re.compile(r"\[([A-Za-z\-' ]+, [A-Za-z\-' ]+) \((M|F)\) DOB: ([0-9\/]+) (.+, .+ [0-9]{4})\] (.*)$", re.IGNORECASE)
# this is the same regex as in athen/server/roundcube/athen.js

m = subject_re.match(msg['Subject'])

if m:
    doc = {}
    doc['patient_name'] = m.group(1)
    doc['sex'] = m.group(2)
    doc['dob'] = m.group(3)
    doc['address'] = m.group(4)
    subject = m.group(5)
    doc['recipient'] = receipient_name
    try:
        hub = util.LDAP()
        r = hub.query(util.base_dn,"(mail=%s)",recipient_email,fields=['providerNumber'])
        if r:
            doc['provider_number'] = r[0]['providerNumber']
    except:
        logging.exception("couldn't get provider number from LDAP server - left blank")
    text = ""
    textpart = None
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            text += part.get_payload()
            textpart = part
    doc['text'] = text
    pittext = pit.make(doc)
    attachment = email.mime.application.MIMEApplication(pitfile,_subtype="x-pit")
    attachment['Content-Disposition'] = 'attachment'
    mainmail = email.mime.text.MIMEText(text)
    mainmail['Content-Disposition'] = "inline"
    newmsg = email.mime.multipart.MIMEMultipart()
    newmsg['Subject'] = subject
    newmsg['To'] = msg['To']
    newmsg['From'] = msg['From']
    if 'Message-Id' in msg:
        newmsg['Message-Id'] = msg['Message-Id']
    else:
        newmsg['Message-Id'] = email.utils.make_msgid()
    if "Reply-To" in msg:
        newmsg['Reply-To'] = msg['Reply-To']
    newmsg['Disposition-Notification-To'] = msg['From']
    newmsg['X-Athen-Security'] = 'secure'
    newmsg.attach(mainmail)
    newmsg.attach(attachment)
    msg = newmsg
    smtp = util.SMTP(HIGHSEC_SERVER)    
elif 'X-Athen-Security' in msg and msg['X-Athen-Security'] == 'secure':
    smtp = util.SMTP(HIGHSEC_SERVER)
else:
    secure = False
    for part in msg.walk():
        if part.get_content_type() == 'application/x-pit': # FIXME: or the other types we will support
            secure = True
    if secure:
        smtp = util.SMTP(HIGHSEC_SERVER)
    else:
        # it's not a clinical message, so pass through unaltered to the low-security
        # server
        smtp = util.SMTP(LOWSEC_SERVER)
smtp.sendmail(sender,[receipient], msg.as_string())
smtp.close()


