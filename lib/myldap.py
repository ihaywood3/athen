"""
An LDAP wrapper that is a bit more Pythonic and easier to manage than the base interface
"""

import ldap, ldap.filter
import time

FIELD_CONVERSIONS = [('organization', 'o'), ('surname', 'sn'), ('cn', 'commonName')]

PUBLIC_LDAP_SERVER='ldaps://localhost/'
#PUBLIC_LDAP_SERVER='ldaps://athen.email/'
PRIVATE_LDAP_SERVER='ldapi:///'
PRIVATE_LDAP_USER='cn=admin,dc=athen,dc=email'



def ldap_time():
    return time.strftime("%Y%m%d%H%M%SZ",time.gmtime())

def makelist(v):
    if not type(v) is list:
        return [str(v)]
    else:
        return v

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


PUBLIC_BASE_DN = Ldap_DN('dc=athen,dc=email')

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
    
class LDAP:
    """a thin wrapper around the LDAP connector
    """

    def __init__(self, local=False, password=""):
        """
        local: if True use server of same host
        False: use the public server at athen.email
        """
        if local:
            self.conn = ldap.initialize(PRIVATE_LDAP_SERVER)
            self.conn.simple_bind_s(PRIVATE_LDAP_USER,password)
        else:
            self.conn = ldap.initialize(PUBLIC_LDAP_SERVER)

    def query(self,query_base=None,query=None,*args,**kwargs):
        if query_base is None:
            query_base = config.base_dn
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
        
    def delete(self, dn):
        self.conn.delete_s(str(dn))
        
