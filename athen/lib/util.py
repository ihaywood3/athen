# -*- coding: utf-8 -*-
"""general utilities for use in the HUB and the server code"""


import hashlib, binascii, os, re, random, os.path, sys, smtplib, email, email.utils, time, tempfile, socket, sqlite3, logging, datetime, math
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import email.utils

SWEARWORDS = ['SHIT', 'FUCK', 'CUNT', 'TWAT']

DEFAULT_TO= "ian@haywood.id.au"
DEFAULT_FROM="ian@haywood.id.au"
DEFAULT_SERVER="haywood.id.au"

NONCELENGTH=10
            

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

def assemble_basic_email(subject, text):
    msg = MIMEText(text)
    msg["Date"]=email.utils.formatdate(localtime=True)
    msg["Subject"]=subject
    return msg



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
        nonce = ''.join(random.choice(alphas) for _ in range(0,NONCELENGTH))
    return nonce


    
class AthenError(Exception):

    def __init__(self, err, field=None, data=None, template=None):
        self.err = err
        self.field = field
        self.data = data
        if self.data is None: self.data = {}
        self.template = None

    def __str__(self):
        if self.field is None:
            return self.err
        else:
            return repr((self.err, self.field, self.data))

    def __repr__(self):
        return repr((self.err, self.field, self.data))

# values from /usr/include/sysexits.h
EX_DATAERR=65 # data format error */
EX_NOINPUT=66 # cannot open input */
#define EX_NOUSER	67	/* addressee unknown */
#define EX_NOHOST	68	/* host name unknown */
#define EX_UNAVAILABLE	69	/* service unavailable */
EX_SOFTWARE=70 # internal software error */
#define EX_OSERR	71	/* system error (e.g., can't fork) */
#define EX_OSFILE	72	/* critical OS file missing */
#define EX_CANTCREAT	73	/* can't create (user) output file */
#define EX_IOERR	74	/* input/output error */
EX_TEMPFAIL=75 # temp failure; user is invited to retry */
#define EX_PROTOCOL	76	/* remote error in protocol */
#define EX_NOPERM	77	/* permission denied */
#define EX_CONFIG	78	/* configuration error */


class LoginRequiredError(Exception):
    """Special error for when the user needs to log in again
    """
    pass
    
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
                    raise AthenError("{} with value of {} is not valid".format(nice_name,repr(data[k])), k, data)
            data[k] = clean_string(data[k])
        else:
            if mode == 'new' and required:
                raise AthenError(nice_name+" is required", k, data)
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
    reps = int(fields[2])
    try: 
        dk = hashlib.pbkdf2_hmac(algo_names[algo],bytes(password),salt2,reps)
    except AttributeError:
        # FIXME: not available =< 2.7.8 so our own version here
        dk = bytes(password)
        st = time.time()
        et = time.time()
        for i in range(0,reps):
            dk = hashlib.sha512(dk+salt2).digest()
    h = binascii.hexlify(dk)
    return "$"+str(algo)+"$"+str(reps)+"$"+salt+"$"+h+"$"

def create_new_hash(password):
    return make_hash(password,"$1$20$"+make_salt())

def clean_string(s):
    """Remove LDAP and HTML-sensitive chars from a string, plus any other weirdness"""
    s = s.replace("&","and")
    translation_table = dict.fromkeys(list(map(ord, '\\()&*|="<>')), None)
    s = s.translate(translation_table)
    s = "".join(x for x in s if ord(x) > 31)
    return s

REPLACEMENTS={" ":".","-":"_","ß":"ss","Ä":"AE","Ö":"OE","Ü":"UE","ä":"ae",
              "ö":"oe","ü":"ue"}

def make_username(u):
    """Make a free string suitable for a email/UNIX username
    i.e. be really, really tight about allowed characters:
    the lowercase English alphabet, full stop, underscore, and the digits
    and that's it"""
    u = u.lower()
    for k, v in REPLACEMENTS.items():
        u = u.replace(k, v)
    u2 = None
    while u2 != u:
        u2 = u
        u2 = u2.replace("..",".")
        u2 = u2.replace('__','_')
    allowed = 'abcdefghijklmnopqrstuvwxyz._0123456789'
    return "".join(x for x in u if x in allowed)

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

def cprotect(s):
    """make stirng safe for C/Javascript"""
    s = s.replace("\"","\\\"")
    s = s.replace("\n","\\n")
    s = s.replace("\r","")
    return s



DOUBLE_PREFIXES = [("VAN","DER"),("VAN","DEN"),("VAN","DE"),("VAN","HET"),("DE","LA")]

SINGLE_PREFIXES = ["VAN","VON","VAN'T","DE"]

def break_surname(name):
    """
    Break a surname off a firstname
    """
    name = name.upper()
    n = name.split()
    if len(n) == 1:
        return (name,"")
    elif len(n) == 2:
        return (n[0],n[1])
    elif len(n) > 3:
        for prefix1, prefix2 in DOUBLE_PREFIXES:
            if n[-3] == prefix1 and n[-2] == prefix2:
                return (" ".join(n[:-3])," ".join(n[-3:]))
    for prefix1 in SINGLE_PREFIXES:
        if n[-2] == prefix1:
            return (" ".join(n[:-2]),prefix1+" "+n[-1])
    return (" ".join(n[:-1]),n[-1])


# FIXME: make sure targets of this translation are HL7 standard terms
TITLES={"DOCTOR":"DR","DR":"DR","PROF":"PROF","PROFESSOR":"PROF",
        "A/PROF":"APROF","APROF":"APROF","A.PROF":"APROF",
        "REVEREND":"REV","REV":"REV",
        "MR":"MR","MISTER":"MR",
        "MASTER":"MSTR","MSTR":"MSTR",
        "MRS":"MRS","MS":"MS"}

def break_titles(name):
    name = name.upper()
    n = name.split()
    if len(n) > 2 and n[0] == 'ASSOCIATE' and n[1] == 'PROFESSOR':
        return ("APROF"," ".join(n[2:]))
    if len(n) > 2 and n[0] == 'ASSOC' and n[1] == 'PROF':
        return ("APROF"," ".join(n[2:]))
    if len(n) > 2 and n[0] == 'ASSOC.' and n[1] == 'PROF.':
        return ("APROF"," ".join(n[2:]))
    title = n[0]
    if title.endswith("."): title = title[:-1]
    if title in TITLES:
        return (TITLES[title]," ".join(n[1:]))
    else:
        return ("", name)

def break_name(name):
    """
    Break a name into a (title, firstnames, surnames) tuple
    Strips quotes from Outlook style names too

>>> util.break_name("Dr. Ian Haywood")
('DR', 'IAN', 'HAYWOOD')
>>> util.break_name("Dr. Hans van der Waals")
('DR', 'HANS', 'VAN DER WAALS')
>>> util.break_name("Assoc. Prof. Hans van der Waals")
('APROF', 'HANS', 'VAN DER WAALS')
>>> util.break_name("\"de la Roche, Jennifer\"")
('', 'JENNIFER', 'DE LA ROCHE')
    """
    if name[0] == '"' and name[-1] == '"':
        name = name[1:-1]
    name = name.upper()
    commas = [i.strip() for i in name.split(",")]
    if len(commas) == 2:
        surname = commas[0]
        title, firstname = break_titles(commas[1])
    else:
        firstname, surname = break_surname(name)
        title, firstname = break_titles(firstname)
    return (title, firstname, surname)


def fullname(d):
    """
    Reconstruct a standardised title firstname surname 
    space-separated
    cope with values being empty
    d is dictionary keyed title firstname surname
    """
    names = [d.get('title'),d.get('firstname'),d.get('surname')]
    names = [i for i in names if i]
    return " ".join(names)

def parse_date(datestr,lo):
    try:
        for char in ['/','.','\\']:
            try:
                day, month, year = [int(x) for x in datestr.split(char)]
                break
            except: pass
        if year < 25: # FIXME: what year to use
            year = year+2000
        elif year < 100:
            year = year + 1900
        assert year > 1800 and year < 3000
        assert day > 0 and day < 32
        assert month > 0 and month < 13
        return datetime.date(year, month, day)
    except:
        logging.exception("date conversion failed")
        return datetime.date(1990, 1, 1)

class Microformatter(logging.Formatter):
    def __init__(self):
        logging.Formatter.__init__(self,'%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) %(message)s')

    def formatTime(self,record,datefmt=None):
        frac, whole = math.modf(record.created)
        basetime = time.strftime("%d %b %y %I:%M:%S.%%05d %p",time.localtime(record.created))
        basetime = basetime % (frac*100000)
        return basetime


def now_tz():
    """the current time with system-provided timezone"""
    return datetime.datetime.now(datetime.timezone.utc).astimezone()
