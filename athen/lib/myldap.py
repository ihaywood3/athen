"""
An LDAP wrapper that is a bit more Pythonic and easier to manage than the base interface
"""

import ldap3, logging
import time, re
import subprocess

FIELD_CONVERSIONS = [('organization', 'o'), ('surname', 'sn'), ('cn', 'commonName')]

PUBLIC_LDAP_SERVER='ldaps://localhost/'
#PUBLIC_LDAP_SERVER='ldaps://athen.email/'
PRIVATE_LDAP_SERVER='ldapi:///'
PRIVATE_LDAP_USER='cn=admin,dc=athen,dc=email'

SORTABLE_FIELD=re.compile(r"^\{([0-9]+)\}(.*)")

class MyLDAPException(Exception):
    pass

def escape_filter_chars(text):
    escaped = text.replace('\\', '\\5c')
    escaped = escaped.replace('*', '\\2a')
    escaped = escaped.replace('(', '\\28')
    escaped = escaped.replace(')', '\\29')
    escaped = escaped.replace('\x00', '\\00')
    return escaped


def hash_password(passwd):
    """created a salted-SHA1 "SSHA" password hash"""
    # FIXME: find a less fugly way of doing this
    pro = subprocess.Popen(["/usr/sbin/slappasswd","-n","-T","/dev/stdin"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err = pro.communicate(bytes(passwd,"utf-8"))
    if err != b"":
        logging.error(err)
        raise MyLDAPException(err)
    return out

def ldap_time():
    return time.strftime("%Y%m%d%H%M%SZ",time.gmtime())

def makelist(v):
    if not type(v) is list:
        return [str(v)]
    else:
        return v

def _break_field(l):
    m = SORTABLE_FIELD.match(l)
    if m:
        return (int(m.group(1)),m.group(2))
    else:
        return (0,l)
    
def ldap_sort(l):
    """sort a list of string fields using the {n}foo convention
    If no {n}, consider as 0 (i.e head of list)

    >>> ldap_sort(["{3}burble", "{2}baz", "{1}foo"])
    ['foo', 'baz', 'burble']
    """
    assert type(l) is list
    return [i[1] for i in sorted((_break_field(i) for i in l),key=lambda x: x[0])]
    
class Ldap_DN:
    """Wrapper around LDAP domain paths
    """

    def __init__(self, dn):
        """Initialise from a standard DN notation foo=bar,foo=bar"""
        if type(dn) is list:
            self.dn = dn
        else:
            self.dn = [tuple(i.split('=',1)) for i in dn.split(",")]

    def to_str(self):
        """Return to standard notation"""
        return ",".join([escape_filter_chars(i[0])+"="+escape_filter_chars(i[1]) for i in self.dn])


    def __str__(self):
        return self.to_str()
    
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
        dn = the_row['dn']
        self.vals = the_row['attributes']
        self.dn = Ldap_DN(dn)
        self.nvals = {}
        for k, v in list(self.vals.items()):
            k = self.normalise_field_name(k)
            self.nvals[k] = v
        self.modlist = {}
        
    def get_field(self, f, default="",as_list=False):
        f = self.normalise_field_name(f)
        if f in self.nvals:
            r = self.nvals[f]
            if not as_list and len(r) == 1:
                r = r[0]
            return r
        else:
            return default

    def get(self, f, default):
        self.get_field(f, default)
    
    def has_key(self, f):
        f = self.normalise_field_name(f)
        return (f in self.nvals)

    def __contains__(self, key):
        key = self.normalise_field_name(key)
        return (key in self.nvals)
    
    def __getattr__(self, name):
        return self.get_field(name)
    
    def __getitem__(self, name):
        return self.get_field(name)
    
    def set_field(self, name, val):
        nname = self.normalise_field_name(name)
        if nname in self.nvals and self.get_field(nname) == val: return
        self.nvals[nname] = val
        self.vals[name] = val
        self.modlist[name] = val
        
    def __setitem__(self, name, val):
        self.set_field(name, val)
        
    def commit(self):
        self.conn.modify(self.dn,self.modlist)
        self.modlist = {}
        
    def normalise_field_name(self, name):
        if not type(name) is str:
            logging.warn("name {}  not string".format(repr(name)))
            name = str(name)
        name = name.lower()
        for v, c in FIELD_CONVERSIONS:
            if name == v: name = c
        return name
    
    def delete(self):
        self.conn.delete(self.dn)
        
    def __repr__(self):
        return "<Ldap_Row: {}, Vals: {}>".format(repr(self.dn), repr(self.nvals))

    def is_class(self, klass):
        klass = klass.lower()
        oc = self.get_field('objectclass')
        if type(oc) is list:
            for i in oc:
                if i.lower() == klass:
                    return True
        else:
            if str(oc).lower() == klass:
                return True
        return False
    
class LDAP:
    """a thin wrapper around the LDAP connector


    >>> c = LDAP()
    >>> c.query("(o=Test Org Eight)",base="dc=athen,dc=email",fields=["businessCategory"])
    [<Ldap_Row: <LDAP DN: o=Test Org Eight,mxDomain=athen.email,dc=athen,dc=email>, Vals: {'businesscategory': 'General Practice'}>]
    >>> c.close()
    >>> import config
    >>> c = LDAP(dn=config.ldap_user,password=config.password,default_base=config.base_dn)
    >>> newdn = config.base_dn.add("o","Fake Org")
    >>> c.add(newdn,{"objectclass":"organization","o":"Fake Org"})
    >>> c.query(base=newdn)
    [<Ldap_Row: <LDAP DN: o=Fake Org,mxDomain=athen.email,dc=athen,dc=email>, Vals: {...}>]
    >>> c.delete(newdn)
    >>> c.close()
    """

    def __init__(self, host="localhost",dn="", password="", default_base=""):
        """
        host: host to connect to, default is local UNIX socket
        dn: the dn of the user to log in as, default anonymous bind
        password: the password
        default_base: default base DN for searches
        """
        self.server = ldap3.Server(host)
        if dn:
            self.conn = ldap3.Connection(self.server,dn,password,auto_bind=True)
        else:
            self.conn = ldap3.Connection(self.server)
            self.conn.bind()
        self.default_base = default_base

    def query(self,query=None,*args,**kwargs):
        if not 'base' in kwargs:
            query_base = self.default_base
        else:
            query_base = kwargs['base']
        if query is None:
            scope = ldap3.SEARCH_SCOPE_BASE_OBJECT
            query = "(objectclass=*)" 
        elif 'node' in kwargs and kwargs['node'] is True:
            scope = ldap3.SEARCH_SCOPE_BASE_OBJECT
        else:
            scope = ldap3.SEARCH_SCOPE_WHOLE_SUBTREE
        if 'fields' in kwargs:
            fields = kwargs['fields']
        else:
            fields = ldap3.ALL_ATTRIBUTES
        args = tuple(escape_filter_chars(i) for i in args)
        if args:
            query = query % args
        logging.debug("ldap query '{}' using base '{}'".format(query,str(query_base)))
        self.conn.search(str(query_base),query,attributes=fields)
        return [Ldap_Row(x, self) for x in self.conn.response]


    def add(self, dn, data):
        oc = data.pop("objectclass")
        res = self.conn.add(str(dn),oc,data)
        if not res:
            logging.debug("LDAP add failed {}".format(repr(self.conn.result)))
            raise MyLDAPException(self.conn.result)

    def modify(self, dn, modlist):
        modlist = {k:(ldap3.MODIFY_REPLACE, makelist(modlist[k])) for k in modlist}
        res = self.conn.modify(str(dn), modlist)
        if not res:
            logging.debug("LDAP modify failed {}".format(repr(self.conn.result)))
            raise MyLDAPException(self.conn.result)
        
    def get_next_uid(self,the_base,recurring=False):
        """Use a special uidNext node in the LDAP DB to generate the next valid uidNumber

        >>> import config
        >>> c = LDAP(dn=config.ldap_user,password=config.password,default_base=config.public_base_dn)
        >>> c.modify("cn=uidNext,dc=athen,dc=email",{"uidNumber":1105})
        >>> c.get_next_uid(config.public_base.dn)
        1106
        >>> c.close()
        """
        res = self.query("(objectclass=uidNext)",fields=['uidNext'],base=the_base)
        olduid = int(res[0]['uidNumber'] or 0)
        newuid = olduid+1
        modlist = {"uidNext":[(ldap3.MODIFY_ADD, [str(newuid)]),(ldap3.MODIFY_DELETE, [str(olduid)])]}
        try:
            # FIXME: not atomic, need newer version ldap3?
            ret = self.conn.modify(res[0].dn,{"uidNumber":(ldap3.MODIFY_REPLACE,[str(newuid)])})
        except ldap3.LDAPException: # our atomic add/delete failed: we tried to change while someone else was changing
            if recurring:
                raise
            else:
                time.sleep(2)
                newuid = self.get_next_uid(self,the_base,recurring=True)
        return newuid

    def login(self,dn,password):
        """Do a test bind for logging in
        >>> import config
        >>> c = LDAP()
        >>> c.login(config.ldap_user,config.password)
        True
        >>> c.login(config.ldap_user,"its wrong")
        False
"""
        try:
            newconn = ldap3.Connection(self.server,dn,password,auto_bind=True)
            newconn.unbind()
            return True
        except ldap3.LDAPException:
            return False

    def delete(self, dn):
        self.conn.delete(str(dn))

    def close(self):
        self.conn.unbind()

    def __enter__(self):
        return self

    def __exit__(self, typ, val, tb):
        try:
            self.conn.unbind()
        except: pass

    def __del__(self):
        try:
            self.conn.unbind()
        except: pass

            
if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)

