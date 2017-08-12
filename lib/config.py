# configuration file
# remember it is Python code, so True not true, strings must be quoted

# the password for logging onto the LDAP server (usually what you entered during installation)
password = 'denethor'

# the domain we are serving email for
domain = "athen.email"

# True if anyone can submit new organisation (i.e. a public open-access server)
# False you must be logged on as the owner organisation
public_registration = True

# login name of the organisation 'owning' the server (logging on means we can create new orgs)
owner = ""

# the secret key for Flask, always change to some random characters
secret_key = "skfjalosfkepw0scl"

latex_path = '/home/ian/athen/latex_output'

# DONT CHANGE BELOW HERE UNLESS YOU REALLY, REALLY KNOW WHAT YOU ARE DOING
import util, myldap

base_dn = myldap.Ldap_DN('mxdomain=%s,dc=athen,dc=email' % domain)
public_base_dn = myldap.Ldap_DN("dc=athen,dc=email")
ldap_user = "cn=admin,%s" % str(base_dn)
certs=('/etc/ssl/certs/athen.pem','/etc/ssl/private/athen.key')
#public_ldap = "ldaps://hub.athen.email"
#debug = False

# for testing
public_ldap = "ldapi://"
debug = True

