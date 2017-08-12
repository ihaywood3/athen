"""
An LDAP wrapper that is a bit more Pythonic and easier to manage than the base interface
"""

import ldap, ldap.filter
import time
import subprocess

FIELD_CONVERSIONS = [('organization', 'o'), ('surname', 'sn'), ('cn', 'commonName')]

PUBLIC_LDAP_SERVER='ldaps://localhost/'
#PUBLIC_LDAP_SERVER='ldaps://athen.email/'
PRIVATE_LDAP_SERVER='ldapi:///'
PRIVATE_LDAP_USER='cn=admin,dc=athen,dc=email'

def hash_password(passwd):
    """created a salted-SHA1 "SSHA" password hash"""
    # FIXME: find a less fugly way of doing this
    pro = subprocess.Popen(["/usr/sbin/slappasswd","-n","-T","/dev/stdin"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err = pro.communicate(passwd)
    if err != "":
        raise LDAPError(err)
    return out

def ldap_time():
    return time.strftime("%Y%m%d%H%M%SZ",time.gmtime())

def makelist(v):
    if not type(v) is list:
        return [str(v)]
    else:
        return v

class Ldap_DN:
    """Wrapper around LDAP domain paths
    """

    def __init__(self, dn):
        """Initialise from a standard DN notation foo=bar,foo=bar"""
        if type(dn) is list:
            self.dn = dn
        else:
            self.dn = [tuple(i.split('=',1)) for i in dn.split(",")]

    def __str__(self):
        """Return to standard notation"""
        return ",".join([ldap.filter.filter_format("%s=%s",[i[0],i[1]]) for i in self.dn])

    def __getitem__(self, x):
        """Return first domain component matching field name x"""
        for a, b in self.dn:
            if x == a:
                return b
        return None

    def add(self, a, b):
        """add domain path section field a value b"""
        return Ldap_DN([(a,b)]+self.dn)

    def sub(self, n=1):
        """Lop off n domain path components from the end
        i.e. go up the directory tree"""
        return Ldap_DN(self.dn[n:])

    def __repr__(self):
        return "<LDAP DN: {}>".format(str(self))


class Ldap_Row:
    """Wrapper around rows"""

    def __init__(self, the_row, conn):
        self.conn = conn
        dn, self.vals = the_row
        self.dn = Ldap_DN(dn)
        self.nvals = {}
        for k, v in list(self.vals.items()):
            k = self.normalise_field_name(k)
            if len(v) == 1:
                v = v[0]
            self.nvals[k] = v
        self.modlist = []
        
    def get_field(self, f):
        f = self.normalise_field_name(f)
        if f in self.nvals:
            return self.nvals[f]
        else:
            return ""
    
    def has_key(self, f):
        f = self.normalise_field_name(f)
        return self.nvals.has_key(f)

    def __getattr__(self, name):
        return self.get_field(name)
    
    def __getitem__(self, name):
        return self.get_field(name)
    
    def set_field(self, name, val):
        nname = self.normalise_field_name(name)
        if self.nvals[nname] == val: return
        self.nvals[nname] = val
        self.vals[name] = val
        modlist.append((ldap.MOD_REPLACE,name,makelist(val)))
        
    def __setitem__(self, name, val):
        self.set_field(name, val)
        
    def commit(self):
        self.conn.modify(self.dn,self.modlist)
        self.modlist = []
        
    def normalise_field_name(self, name):
        name = name.lower()
        for v, c in FIELD_CONVERSIONS:
            if name == v: name = c
        return name
    
    def delete(self):
        self.conn.delete(self.dn)
        
    def __repr__(self):
        return "<Ldap_Row: {}, Vals: {}>".format(repr(self.dn), repr(self.nvals))

    def is_class(self, klass):
        klass = lower(klass)
        oc = self.get_field('objectclass')
        if type(oc) is list:
            for i in oc:
                if lower(i) == klass:
                    return True
        else:
            if lower(str(oc)) == klass:
                return True
        return False
    
class LDAP:
    """a thin wrapper around the LDAP connector
    """

    def __init__(self, host="ldapi://",dn="", password="", default_base=""):
        """
        host: host to connect tom, default is local UNIX socket
        dn: the dn of the user to log in as, default anonymous bind
        password: the password
        default_base: default base DN for searches
        """
        self.conn = ldap.initialize(host)
        self.conn.simple_bind_s(dn,password)
        self.default_base = default_base

    def query(self,query=None,*args,**kwargs):
        if not 'base' in kwargs:
            query_base = self.default_base
        else:
            query_base = kwargs['base']
        if query is None:
            scope = ldap.SCOPE_BASE
            query = "(&)" # the "absolute true" LDAP expression
        elif 'node' in kwargs and kwargs['node'] is True:
            scope = ldap.SCOPE_BASE
        else:
            scope = ldap.SCOPE_SUBTREE
        if 'fields' in kwargs:
            fields = kwargs['fields']
        else:
            fields = ["*"]
        query = ldap.filter.filter_format(query,args)
        res = self.conn.search_s(str(query_base),scope,query,fields)
        return [Ldap_Row(x, self) for x in res]


    def add(self, dn, data):
        modlist = []
        for k, v in list(data.items()):
            modlist.append((k, makelist(v)))
        self.conn.add_s(str(dn),modlist)

    def modify(self, dn, modlist):
        if type(modlist) is dict:
                modlist = [(ldap.MOD_REPLACE, k, makelist(v)) for k, v in list(modlist.items())]
        self.conn.modify_s(str(dn), modlist)

    def get_next_uid(self,recurring=False):
        """Use a special uidNext node in the LDAP DB to generate the next valid uidNumber"""
        dn = "cn=uidNext,dc=athen,dc=email"
        res = self.query(base=dn,fields=['uidNext'])
        olduid = int(res[0]['uidNext'])
        newuid = olduid+1
        modlist = [(ldap.MOD_ADD, "uidNext", str(newuid)),(ldap.MOD_DELETE, "uidNext", str(olduid))]
        try:
            self.conn.modify_s(dn,modlist)
        except ldap.LDAPError: # our atomic add/delete failed: we tried to change while someone else was changing
            if recurring:
                raise
            else:
                time.sleep(2)
                newuid = self.get_next_uid(self,True)
        return newuid

    def login(self,dn,password):
        """Do a test bind for logging in"""
        try:
            newconn = ldap.initialize(self.host)
            newconn.simple_bind_s(dn,password)
            newconn.unbind_s()
            return True
        except ldap.LDAPError:
            return False

    def delete(self, dn):
        self.conn.delete_s(str(dn))

    def close(self):
        self.conn.unbinds_s()
        
