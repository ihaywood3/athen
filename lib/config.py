# configuration file
# remember it is Python code, so True not true, strings must be between "

# the password for logging onto the LDAP server (usually what you entered during installation)
password = "denethor"

# the domain we are serving email for
domain = "athen-test"

# True if anyone can submit new organisation (i.e. a public open-access server)
# False you must be logged on as the owner organisation
public_registration = True

# login name of the organisation 'owning' the server (logging on means we can create new orgs)
owner = ""

# the secret key for Flask, always change to some random characters
secret_key = "skfjalosfkepw0scl"

# where to put the welcome letters
latex_path = "/home/athen/latex_output"

# the source address for letters, lines separated by \\\\
letter_origin_address = "ATHEN \\\\ 1 Foo St \\\\ Nowhere"

# the name below the signature on welcome letters
letter_signature = "Ian Haywood"

# the name of the work within the text of the welcome letter
letter_network_name = "ATHEN network"

# debugging, True or False
debug = False

# DONT CHANGE BELOW HERE UNLESS YOU REALLY, REALLY KNOW WHAT YOU ARE DOING
import util, myldap
import logging, logging.handlers

base_dn = myldap.Ldap_DN('mxdomain=%s,dc=athen,dc=email' % domain)
public_base_dn = myldap.Ldap_DN("dc=athen,dc=email")
ldap_user = "cn=admin,%s" % str(public_base_dn)
certs=('/etc/ssl/certs/athen.pem','/etc/ssl/private/athen.key')
http_socket='/var/run/athen/athen.sock'

if debug:
    public_ldap = "ldapi://"
else:
    public_ldap = "ldaps://hub.athen.email/"


version = "0.0.1"

logger = logging.getLogger()
fmtr = util.Microformatter()
if debug:
    logger.setLevel(logging.DEBUG)
    lsh = logging.StreamHandler()
    lsh.setFormatter(fmtr)
    logger.addHandler(lsh)
else:
    # the user is welcome to wade through the Python logging documentation
    # and change the logging arrangments to whatever their heart desires
    logger.setLevel(logging.DEBUG)
    h = logging.handlers.RotatingFileHandler("/var/log/athen/python.log", maxBytes=100000, backupCount=9)
    h.setFormatter(fmtr)
    logger.addHandler(h)
