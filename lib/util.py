"""general utilities for use in the HUB and the server code"""


import hashlib, binascii, os, re, random, os.path, sys, smtplib, email, email.utils, time, tempfile, socket
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import email.utils

SWEARWORDS = ['SHIT', 'FUCK', 'CUNT', 'TWAT']

DEFAULT_TO= "ian@haywood.id.au"
DEFAULT_FROM="ian@haywood.id.au"
DEFAULT_SERVER="haywood.id.au"


class SMTP(smtplib.SMTP):
    """A simple subclass to support SMTP over UNIX sockets
    If the port is set to -1, then the host is considered
    a UNIX path"""
    
    def _get_socket(self, host, port, timeout):
        "if port=-1, then host is actually a UNIX socket path"
        if port == -1:
            # use UNIX socket type
            sock = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            if timeout != socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(float(timeout))
            sock.connect(host)
            return sock
        else:
            # just use the ancestor for TCP/IP
            return smtplib.SMTP._get_socket(self, host, port, timeout)
            

def send_mail(subject, text, dvi=None, host=None):
    msg = MIMEMultipart()
    msg['From']=DEFAULT_FROM
    msg["To"]=DEFAULT_TO
    msg["Date"]=email.utils.formatdate(localtime=True)
    msg["Subject"]=subject
    msg.attach(MIMEText(text))
    if dvi:
        msg.attach(MIMEApplication(
            dvi,
            "x-dvi",
            Content_Disposition='attachment; filename="invite.dvi"',
            name="invite.dvi"
            ))
    if host is None:
        host=DEFAULT_SERVER
    smtp = SMTP(host)
    smtp.starttls()
    smtp.sendmail(DEFAULT_FROM, [DEFAULT_TO], msg.as_string())
    smtp.close()

def make_dvi(latex):
    fd, tmpf = tempfile.mkstemp(".tex")
    tmpf_dvi = tmpf[:-3]+'dvi' 
    os.write(fd, latex)
    os.close(fd)
    os.chdir(os.path.dirname(tmpf))
    os.system("latex {}".format(tmpf))
    with open(tmpf_dvi,'r') as f:
        dvi = f.read()
    os.unlink(tmpf)
    os.unlink(tmpf_dvi)
    return dvi

def make_nonce():
    nonce = SWEARWORDS[0]
    alphas = [chr(i) for i in range(ord('A'),ord('Z')+1)]
    alphas.extend([str(i) for i in range(0,10)])
    while check_swear(nonce):
        nonce = ''.join(random.choice(alphas) for dum in range(1,10))
    return nonce



    
class AthenError(Exception):

    def __init__(self, err, field=None, data=None):
        self.err = err
        self.field = field
        self.data = data
        if self.data is None: self.data = emptydict()

    def __str__(self):
        return repr((self.err, self.field, self.data))

    def __repr__(self):
        return repr((self.err, self.field, self.data))


def validate_fields(request,mode,schema):
    data = {}
    for k, required, regex, nice_name in schema:
        x = request.form.get(k, None)
        if not (x is None or x == ""): data[k] = x
    for k, required, regex, nice_name in schema:
        if k in data:
            if not regex is None:
                m = re.match(regex, data[k])
                if m is None:
                    raise AthenError("{} with value of {} is not valid".format(nice_name,repr(data[k])), k, emptydict(data))
            data[k] = clean_string(data[k])
        else:
            if mode == 'new' and required:
                raise AthenError(nice_name+" is required", k, emptydict(data))
    return data
    


def check_swear(s):
    for i in SWEARWORDS:
        if i in s:
            return True
    return False

def make_salt():
    return binascii.hexlify(os.urandom(16))

def make_hash(password,stub):
    fields = stub.split("$")
    algo = int(fields[1])
    algo_names = ['invalid','sha256','sha512']
    salt = fields[3]
    salt2 = binascii.unhexlify(salt)
    reps = int(fields[2])*10000
    try: 
        dk = hashlib.pbkdf2_hmac(algo_names[algo],bytes(password),salt2,reps)
    except AttributeError:
        # FIXME: not available =< 2.7.8 so our own version here
        dk = bytes(password)
        for i in range(0,reps):
            dk = hashlib.sha512(dk+salt2).digest()
    h = binascii.hexlify(dk)
    return "$"+str(algo)+"$"+str(reps)+"$"+salt+"$"+h+"$"

def create_new_hash(password):
    return make_hash(password,"$1$20$"+make_salt())

def clean_string(s):
    """Remove LDAP and HTML-sensitive chars from a string, plus any other whitespace or weirdness"""
    translation_table = dict.fromkeys(map(ord, '()&*,/|="<>'), None)
    s = s.translate(translation_table)
    s = filter(lambda x: ord(x) > 31 and ord(x) < 126, s)
    return s

def make_username(u):
    """Make a free string suitable for a email/UNIX username"""
    u = u.lower()
    u = u.replace(" ",".")
    u = u.replace("-","_")
    u2 = u.replace("..",".").replace('__','_')
    while u2 != u:
        u = u2
        u2 = u.replace("..",".")
    allowed = 'abcdefghijklmnopqrstuvwzyz._'
    u = filter(lambda x: x in allowed,u)
    return u

def latexise(v):
    """Make string safe for LaTeX"""
    if v is None: return ""
    v = v.replace("\\", "BACKSSLASH")
    for i in ["$", "%", "&", "{", "_"]:
        v = v.replace(i, "\\"+i)
    v = v.replace("~", "\\textasciitilde ")
    v = v.replace(">", "\\textgreater ")
    v = v.replace("<", "\\textless ")
    v = v.replace("BACKSSLASH", "\\textbackslash ")
    return v
