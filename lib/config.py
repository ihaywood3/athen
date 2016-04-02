# configuration file
# remember it is Python code, so True not true, string smust be quoted


# the password for logging onto the LDAP server (usually what you entered during installation)
password = 'denethor'


# the domain we are serving email for
domain = "athen.net.au"

# True if anyone can submit new organisation (i.e. a public open-access server)
# False you must be logged on as the woner organisation
public_registration = True

# name of the organisation 'owning' the server (logging on means can create new orgs)
owner = ""

# the secret key for Flask, always change to some random characters
secret_key = "skfjalosfkepw0scl"

# DONT CHANGE BELOW HERE UNLESS YOU KNOW WHAT YOU ARE DOING
import util

base_dn = util.Ldap_DN("dc=nodomain")
ldap_user = "cn=admin,dc=nodomain"
certs=('/home/ian/athen/hub/tests/cert.pem','/home/ian/athen/hub/tests/key.pem')
upload_file='/home/ian/athen.upload.dat'
athen_api_url = 'https://127.0.0.1:5000/api' # FIXME: will be https://athen.email/api/'
