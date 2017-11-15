"""
A mail filtering system to add medical-compliant attachments where appropriate
called from server/python/deliver.py in incoming mail filtering
"""

import io, re, logging
from pgp_mime.myemail import email_targets, email_sources
from collections import defaultdict
import email.mime.multipart
import email.utils
from registry import *
import util, myldap, config, htmlparse, textparse


SUBJECT_RE=re.compile(r"\[([A-Za-z\-' ]+, [A-Za-z\-' ]+) \((M|F|O|A)\) DOB: ?([0-9\/]+) (.+, .+ [0-9]{4})\] (.*)$", re.IGNORECASE)
SUBJECT_RE_NOADDR=re.compile(r"\[([A-Za-z\-' ]+, [A-Za-z\-' ]+) \((M|F|O|A)\) DOB: ?([0-9\/]+) *\] (.*)$", re.IGNORECASE)

logger = logging.getLogger(__name__)

def enrich_name_via_ldap(name):
    try:
        with myldap.LDAP(host=config.public_ldap,default_base=config.public_base_dn) as hub:
            logger.info("looking up {} in LDAP".format(name["email"]))
            res = hub.query("(mail=%s)",name["email"])
            if res:
                if "providerNumber" in res[0]:
                    name['provider_number'] = res[0]['providerNumber']
                    logger.info("Found directly provider number {}".format(res[0]['providerNumber']))
                else:
                    # its probably an organisational email
                    # but could the person named be an employee of this org, and so with a PN?
                    fullname = name["firstname"] + " " + name["surname"]
                    if len(fullname) > 5:
                        logger.info("searching using name {}".format(fullname))
                        res2 = hub.query("(cn=%s)",fullname,base=res[0].dn,fields=['providerNumber'])
                        if res2 and "providerNumber" in res2[0]:
                            name['provider_number'] = res2[0]['providerNumber']
                            logger.info("Found directly provider number {}".format(res2[0]['providerNumber']))
                # we were provided no name at all, use LDAP to give us a real name if we can
                if not name['surname']:
                    if 'sn' in res[0]:
                        name['surname'] = res[0]['sn']
                        name['firstname'] = res[0]['givenName']
                        logger.info("Using LDAP derived name {} {}".format(res[0]['givenName'],res[0]['sn']))
                    if 'o' in res[0]:
                        name['surname'] = res[0]['o']
                        name['firstname'] = ""
                        logger.info("Using LDAP derived org name {}".format(res[0]['o']))
        return name
    except:
        logger.exception("error finding provider number from public LDAP")


def _worker(u_ctx,msg,ld):
    """
    Process a message using the handlers that
    have been linked in by imported modules
    Writes to the provided LogicalDocument
    """
    if "Date" in msg and not ld.has('document_time'):
        ld.document_time = email.utils.parsedate_to_datetime(msg['Date'])
    if "Subject" in msg and not ld.has('patient_name'):
        m = SUBJECT_RE.match(msg['Subject'])
        if m:
            ld.patient_name = m.group(1)
            ld.sex = m.group(2)
            ld.birthdate = util.parse_date(m.group(3),ld)
            ld.patient_address = m.group(4)
            logger.info("Matched email subject patient_name '{}' sex '{}' birthdate '{}' address '{}'".format(ld.patient_name,ld.sex,ld.birthdate,ld.patient_address))
        m = SUBJECT_RE_NOADDR.match(msg['Subject'])
        if m:
            ld.patient_name = m.group(1)
            ld.sex = m.group(2)
            ld.birthdate = util.parse_date(m.group(3),ld)
            logger.info("Matched email subject patient_name '{}' sex '{}' birthdate '{}' no address".format(ld.patient_name,ld.sex,ld.birthdate))
    if "To" in msg and not ld.has("recipient"):
        recipient_email = u_ctx['USER']+'@'+config.domain
        for recipient_name, rep_email2 in email_targets(msg):
            if rep_email2 == recipient_email:
                r = defaultdict(lambda: '')
                r['email'] = recipient_email
                if recipient_name:
                    r['title'], r['firstname'], r['surname'] = util.break_name(recipient_name)
                r = enrich_name_via_ldap(r)
                ld.recipient = r
                break
    for sender_hdr in ["X-OpenPGP-Signer","From"]:
        if not ld.has("sender") and sender_hdr in msg:
            senders = list(email_sources(msg,field=sender_hdr))
            if senders:
                sender_name, sender_email = senders[0]
                s = defaultdict(lambda: '')
                s['email'] = sender_email
                if sender_name:
                    s["title"], s["firstname"], s["surname"] = util.break_name(sender_name)
                s = enrich_name_via_ldap(s)
                ld.sender = s
    if msg.is_multipart():
        if msg.get_content_type() == 'multipart/alternative':
            one_with_html = None
            one_with_attachments = None
            children = list(msg.get_payload())
            if len(children) == 1:
                process(children[0],ld)
            else:
                for child in children:
                    if child.is_multipart():
                        grandchildren = list(child.walk())
                    else:
                        grandchildren = [child]
                    for part in grandchildren:
                        if part.get_content_type() == 'text/html':
                            one_with_html = child
                        if part.get_content_disposition() == 'attachment':
                            one_with_attachments = child
                if one_with_html and one_with_attachments and (one_with_html == one_with_attachments):
                    process(one_with_html,ld)
                elif one_with_html and one_with_attachments is None:
                    process(one_with_html,ld)
                elif one_with_attachments and one_with_html is None:
                    process(one_with_attachments)
                else:
                    # Aargh! we can't safely decide which alternative to use
                    raise NotPossible
        else:
            for child in msg.get_payload():
                process(child,ld)
    elif msg.get_content_maintype() == 'image':
        data = msg.get_content(decode=True)
        if len(data) < 16384 and msg.get_content_disposition() == 'inline':
            # small images of this type are used as watermarks by some senders
            # so we ignore them
            logger.info("Ignored small image attachment")
        else:
            # but any other image (attachment, or bigger than 16K), we bork
            raise NotPossible
    elif msg.get_content_type() in registry_mime:
        logger.info("processing attachment by MIME {}'".format(msg.get_content_type()))
        payload = msg.get_payload(decode=True) # this alawys returns a bytes. grr.
        if msg.get_content_maintype() == 'text': # for text really means sense to be a str
            charset = msg.get_charset()
            if charset:
                charset = charset.input_charset
            if not charset:
                charset = 'us-ascii'
            payload = str(payload,charset)
        # other amjor types the handler here is expected to cope with a bytes
        registry_mime[msg.get_content_type()] (payload,ld)
    else:
        unprocessed = True
        fname = msg.get_filename()
        if fname:
            fname = fname.lower()
            for k in registry_filetypes:
                if fname.endswith(k):
                    logger.info("attached file {} ending with {}, processing".format(fname,k))
                    unprocessed = False
                    registry_filetypes[k] (msg, ld)
                    break
        if unprocessed:
            raise NotPossible()

def process(u_ctx,msg,udb):
    global logger
    if not u_ctx['deliveryFormat']:
        # user doesn't want special delivery formats
        return msg
    ld = LogicalDocument(udb)
    try:
        _worker(u_ctx,msg,ld)
        for i in myldap.ldap_sort(u_ctx['deliveryFormat']):
            try:
                if i in get_all_outputs():
                    attachment = call_output(i, ld)
                    logging.info("generated attachment type {}".format(i))
                    if attachment:
                        attached = False
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == 'multipart/mixed':
                                    part.attach(attachment)
                                    attached = True
                                    break
                        if not attached:
                            # original message isn't multipart/mixed...messy
                            # make a new packet
                            newmsg = email.mime.multipart.MIMEMultipart(_subtype='mixed')
                            # copy across all the headers except the content type and encoding
                            for hdr, val in msg.items():
                                if hdr.lower() not in ['content-type','content-transfer-encoding','content-disposition']:
                                    newmsg[hdr] = val
                                    del msg[hdr]
                            if not 'Content-Disposition' in msg:
                                msg['Content-Disposition'] = 'inline'
                            # and add back in as attachment to our new msg
                            newmsg.attach(msg)
                            newmsg.attach(attachment)
                            msg = newmsg
                        break
            except NotPossible:
                pass
    except NotPossible:
        pass
    return msg
    
