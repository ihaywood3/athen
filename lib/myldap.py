"""
An LDAP wrapper that is a bit more Pythonic and easier to manage than the base interface
"""

import ldap, ldap.filter, time

FIELD_CONVERSIONS = [('organization', 'o'), ('surname', 'sn'), ('cn', 'commonName')]

    
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

class Ldap_Row:
    """Wrapper around rows"""
    
    def __init__(self, the_row, conn):
        self.conn = conn
        self.dn, self.vals = the_row
        self.dn = Ldap_DN(dn)
        self.nvals = {}
        for k, v in vals.items():
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
        
    def normalise_names(self, name):
        name = lower(name)
        for v, c in FIELD_CONVERSIONS:
            if name == v: name = c
        return name
    
class LDAP:
    """a thin wrapper around the LDAP connector
    """

    def __init__(self, local=False, password=""):
        if local:
            self.conn = ldap.initialize('ldapi:///')
            self.conn.simple_bind_s('cn=admin,dc=athen,dc=net,dc=au',password)
        else:
            self.conn = ldap.initialize("ldaps://athen.email/")

    def query(self,query_base=None,query=None,*args,**kwargs):
        if query_base is None:
            query_base = base_dn
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
        return map(lambda x: Ldap_Row(x, self), res)


    def add(self, dn, data):
        modlist = []
        for k, v in data.items():
            modlist.append((k, makelist(v)))
        self.conn.add_s(str(dn),modlist)

    def modify(self, dn, modlist):
        if type(modlist) is dict:
                modlist = [(ldap.MOD_REPLACE, k, makelist(v)) for k, v in modlist.items()]
        self.conn.modify_s(str(dn), modlist)