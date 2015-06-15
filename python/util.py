import tempfile, os, os.path, subprocess, logging, sys, ldap

class Spooler:
    """A directory system for spooling files, fairly basic"""

    def __init__(self, directory):
        self.dir = directory
        self.no = 0
        
    def unique(self):
        """Return a unique filename in the directory"""
        self.no = self.no + 1
        n = str(os.getpid())+'-'+str(self.no)
        # because we are using the PID, we know for the life of this process no-one else is going to grab the filename
        if os.path.exists(n):
            return self.unique()
        else:
            return n

    def __iter__(self):
        """List all the files and delete them after listing"""
        for i in os.listdir(self.dir):
            n = os.path.join(self.dir,i)
            yield n
            os.unlink(n)

def gpg(args,file_in=None):
    s = subprocess.Popen(['usr/bin/gpg']+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.PIPE)
    (out, err) = s.communicate(file_in)
    if s.returncode != 0:
        logging.critical("GPG failed with return code %d" % s.returncode)
        logging.critical("stderr %r" % err)
        sys.exit(1)
    return out

def exe(args,file_in=None):
    """Execute something. Log and die if there is a problem"""
    s = subprocess.Popen(args,stderr=subprocess.PIPE,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    (out, err) = s.communicate(file_in)
    if s.returncode != 0:
        logging.critical("%r failed with code %d" % (args,s.returncode))
        logging.critical("stderr %r" % err)
        sys.exit(1)
    return out

class LDAP:
    """Very very high level interface to the LDAP store"""

    def __init__(self):
        try:
            self.l = ldap.open("127.0.0.1")
            self.l.simple_bind_s("","")  # anonymous bind
        except ldap.LDAPError:
            logging.exception("failed to open LDAP",exc_info=True)
            sys.exit(1)
            
    def search(self,query,attrs=None,max_entries=100):
        base = "dc=athen,dc=net,dc=au"
        scope = ldap.SCOPE_SUBTREE
        try:
            result = self.l.search_ext_s(base, scope, query, attrs, 0, None, None, 60, max_entries)
            return [i[1] for i in result]
        except ldap.LDAPError:
            logging.exception("LDAP error on %s" % query)
            sys.exit(1)
