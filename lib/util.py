"""general utilities for use in the HUB and the server code"""

import ldap, ldap.filter
import hashlib, binascii, os, re, random, os.path, sys, smtplib, email, email.utils, time, tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import email.utils
import collections

SWEARWORDS = ['SHIT', 'FUCK', 'CUNT', 'TWAT']

DEFAULT_TO= "ian@haywood.id.au"
DEFAULT_FROM="ian@haywood.id.au"
DEFAULT_SERVER="haywood.id.au"


def emptydict(d=None):
    if d is None: d = {}
    return collections.defaultdict(lambda x: "", d)

def send_mail(subject, text, dvi=None):
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
    smtp = smtplib.SMTP(DEFAULT_SERVER)
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

    
def ldap_time():
    return time.strftime("%Y%m%d%H%M%SZ",time.gmtime())

def e(x,*args):
    return ldap.filter.filter_format(x,args)

class Ldap_DN:
    """Wrapper around LDAP doamin paths
    """

    def __init__(self, dn):
        """Initialise from a standard DN notation foo=bar,foo=bar"""
        if type(dn) is list:
            self.dn = dn
        else:
            self.dn = [tuple(i.split('=',1)) for i in dn.split(",")]

    def __str__(self):
        """Return to standard notation"""
        return ",".join([e("%s=%s",i[0],i[1]) for i in self.dn])

    def __getitem__(self, x):
        """Return first domain component matching field name x"""
        for a, b in self.dn:
            if x == a:
                return b
        return None

    def add(self, a, b):
        """add domain path section field a value b"""
        return Ldap_DN([(a,b)]+self.dn)

    def sub(self, n):
        """Lop off n domain path components from the end
        i.e. go up the directory tree"""
        return Ldap_DN(self.dn[n:])

class LDAP:
    """a thin wrapper around the LDAP connector
    """

    def __init__(self, local=False, password=""):
        if local:
            self.conn = ldap.initialize('ldapi:///')
            self.conn.simple_bind_s('cn=admin,dc=athen,dc=net,dc=au',password)
        else:
            self.conn = ldap.initialize("ldaps://hub.athen.email/")

    def query(self,base_dn,query=None,*args,**kwargs):
        if query is None:
            node = True
            query = "(&)" # the "absolute true" LDAP expression
        if 'node' in kwargs and kwargs['node'] is True:
            scope = ldap.SCOPE_BASE
        else:
            scope = ldap.SCOPE_SUBTREE
        if 'fields' in kwargs:
            fields = kwargs['fields']
        else:
            fields = ["*"]
        query = ldap.filter.filter_format(query,args)
        res = self.conn.search_s(str(base_dn),scope,query,fields)
        return map(self.fold_dn,res)

    def fold_dn(self,i):
        dn, vals = i
        vals2 = emptydict()
        for k, v in vals.items():
            if len(v) == 1:
                vals2[k] = v[0]
            else:
                vals2[k] = v
        vals2['dn'] = Ldap_DN(dn)
        return vals2

    def add(self,dn, data):
        modlist = []
        for k, v in data.items():
            if type(v) is list:
                modlist.append((k, v))
            else:
                modlist.append((k, [str(v)]))
        self.conn.add_s(str(dn),modlist)

    def modify(self,dn, data):
        modlist = []
        for k, v in data.items():
            if not type(v) is list:
                v = [str(v)]
            modlist.append((ldap.MOD_REPLACE,k,v))
        self.conn.modify_s(str(dn), modlist)

    
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
    return emptydict(data)
    


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
    reps = int(fields[2])*10000
    dk = hashlib.pbkdf2_hmac(algo_names[algo],bytes(password),binascii.unhexlify(salt),reps)
    h = binascii.hexlify(dk)
    return "$"+str(algo)+"$"+str(reps)+"$"+salt+"$"+h+"$"

def create_new_hash(password):
    return make_hash(password,"$1$20$"+make_salt())

def clean_string(s):
    """Remove LDAP and HTML-sensitive chars from a string"""
    translation_table = dict.fromkeys(map(ord, '!#(){}^&*|=+\n\r\t";:<>,'), None)
    return s.translate(translation_table)

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
