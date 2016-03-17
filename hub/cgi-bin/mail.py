#!/usr/bin/python

"""General wrapper around emailing sending signing and verifying"""

from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import email.utils, os, os.path, atexit
from M2Crypto import BIO, Rand, SMIME

def makebuf(text):
    return BIO.MemoryBuffer(text)
    
rand_file = os.path.expanduser("~/randpool.dat")

if not os.path.exists(rand_file):
    Rand.rand_seed(os.urandom (1024))
else:
    Rand.load_file(rand_file, -1)

atexit.register(lambda x: Rand.save_file(x), rand_file)

def prepare_smime(to, fro, subject, text, signer_key, signer_cert):
    # Make a MemoryBuffer of the message.
    buf = makebuf(text)
    # Instantiate an SMIME object; set it up; sign the buffer.
    s = SMIME.SMIME()
    s.load_key(signer_key, signer_cert)
    p7 = s.sign(buf, SMIME.PKCS7_DETACHED)
    # Recreate buf.
    buf = makebuf(text)
    # Output p7 in mail-friendly format.
    out = BIO.MemoryBuffer()
    out.write('From: {}\nTo: {}\nSubject: {}\nDate: {}\n'.format(fro, to, subject, email.utils.formatdate(localtime=True))
    s.write(out, p7, buf)
    return out.read()


def send_mail(to, fro, subject, text, signer_key, signer_cert, dvi=None):
    msg = MIMEMultipart()
    msg.attach(MIMEText(text))
    if dvi:
        msg.attach(MIMEApplication(
            dvi,
            "x-dvi",
            Content_Disposition='attachment; filename="invite.dvi"',
            name="invite.dvi"
            )
    smime = prepare_smime(to, fro, subject, msg.as_string(), signer_key, signer_cert)
    smtp = smtplib.SMTP(DEFAULT_SERVER)
    smtp.starttls()
    smtp.sendmail(fro, [to], smime)
    smtp.close()
