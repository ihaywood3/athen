#!/usr/bin/python
"""
The HUB is an OpenLDAP server which is updated by HTTPS requests authenticated via X.509 client certificate.
Flask is still used even though there is no user-visble web pages, for consistency with the server mainly
"""

import sys, os

import M2Crypto.X509

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

from flask import Flask, session, redirect, url_for, escape, request, render_template_string, g, flash

sys.path.append('../../lib')
from util import *
import config

app = Flask(__name__)



mail_text_template ="""
Organisation Name: {{o}}
Address: {{street}}, {{l}} {{postalCode}} {{st}}
Telephone: {{telephoneNumber}}
Fax: {{facsimileTelephoneNumber}}
Type: {{businessCategory}}
Email : {{mail}}
"""

mail_latex_template = """
\\documentclass[12pt]{letter}
\\signature{Dr. Ian Haywood}
\\address{Ian Haywood \\\\ ATHEN \\\\ 64 Robertson Dr\\\\ Mornington VIC 3931\\\\ Tel. 0359867709}
\\begin{document}
\\begin{letter}{The Practice Manager\\\\ {{o}} \\\\ {{street}} \\\\ {{l}} {{postalCode}} {{st}} }
\\opening{Dear Madam/Sir,}

Your organisation has been registered on the ATHEN network using this postal address.

Your registration code is \\texttt{ {{nonce}} }

If you wish to register, please go to \\texttt{https://athen.org/}, click on `Register' and enter in the code above.

if you did not request registration, plase check if someone in your organisation did register and ask them for more details.

If you have no idea what this letter is about, please contact me on the above address.

\\closing{Yours faithfully,}
\\end{letter}
\\end{document}
"""


schema = {
    "org": [
            ('o', True, None, 'Organisation Name'),
            ('st', True, None, 'State'),
            ('l', True, None, 'Town'),
            ('businessCategory', True, None, 'Business category'),
            ('street', True, None, 'Street'),
            ('postalCode', True, '[0-9]{4}', 'postcode'),
            ('telephoneNumber', False, '[0-9 ]{8,10}', 'Telephone number'),
            ('facsimileTelephoneNumber', False, '[0-9 ]{8,10}', 'Fax number'),
            ('mail', True, '^[A-Za-z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', "Email address")
        ],
    "user": [
            ('givenName', True, None, 'Given name'),
            ('sn',True, None, 'Surname'),
            ('medicalSpecialty', True, None, 'Profession/medical specialty'),
            ('mail', True, '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', "Email address"),
            ('providerNumber', False, '^[0-9]{5,6}[0-9A-Z][A-Z]$', "Medicare provider number")
            ]
    }


def get_ldap():
    """Opens a new LDAP connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'ldap'):
        g.ldap = LDAP(local=True,password='denethor')
    return g.ldap

def get_cert_from_conn(request):
    app.logger.debug(repr(request.environ))
    # FIXME: for testing only, should read from the provided environment
    with open(__location__+"/../tests/cert.pem") as f:
        return f.read()

def calc_mxdomain(request):
    """Examine the provided X.509 certificate and work out which athenMailer base record
    we belong to in the LDAP database"""
    tls_cert_str = get_cert_from_conn(request)
    tls_cert = M2Crypto.X509.load_cert_string(tls_cert_str)
    tls_subject = tls_cert.get_subject()
    mxdomain = tls_subject.CN
    fgr = tls_cert.get_fingerprint(md='sha512')
    # check LDAP for this server, create if not found
    res = g.ldap.query(base_dn,"(&(objectclass=athenMailer)(&(tlsSignature=%s)(mxDomain=%s)))",fgr,mxdomain,fields=['mxdomain','o'])
    if len(res) == 1:
        res = res[0]
        return res['dn']
    if len (res) > 1:
        # Aaargh! should never happen
        s = "multiple entries found for one mxdomain/fingerprint pair mxdomain {} fingerprint {}".format(mxdomain,fgr)
        raise AthenError(s,None)
    if len (res) == 0:
        # check no other domains on same signature
        res = g.ldap.query(base_dn,"(&(objectclass=athenMailer)(tlsSignature=%s))", fgr)
        if len(res) > 0:
            # Aaargh! should never happen
            s = "SECURITY VIOLATION: Another mx domain on the same signature domain 1 {} sig1: {} domain2: {}".format(mxdomain,fgr,repr(res))
            raise AthenError(s,None)
        # check no other domains on a different signature
        res = g.ldap.query(base_dn,"(&(objectclass=athenMailer)(mxDomain=%s))", mxdomain)
        if len(res) > 0:
            s = "SECURITY VIOLATION: Another mx domain on a different signature domain1: {} sig1: {} domain2: {}".format(mxdomin,fgr,repr(res))
            raise AthenError(s,None)
        # OK now safe to create a new athenMailer entry
        new_dn = base_dn.add("mxdomain",mxdomain)
        mlr = {'objectclass':'athenMailer','tlsSignature':fgr,'mxDomain':mxdomain,'tlsCertificate':tls_cert_str,'o':tls_subject.O,'status':'P','timeLastUsed':ldap_time(),'timeCreated':ldap_time()}
        if tls_subject.L: mlr["l"] = tls_subject.L
        if tls_subject.ST: mlr["st"] = tls_subject.ST
        g.ldap.add(new_dn, mlr)
        return new_dn
    
@app.route("/api",methods=["POST"])
def api():
    """Main entrypoint"""
    try:
        typ = request.form['type']
        mode = request.form['mode']
        data = validate_fields(request,mode,schema[typ])
        app.logger.debug("dict after validation {}".format(repr(data)))
        get_ldap()
        mailer_dn = calc_mxdomain(request)
        data['timeLastUsed'] = ldap_time()
        if typ == "org":
            new_dn = mailer_dn.add("o",data["o"])
            if mode == "new":
                # check if exists: note checking all organisations in all mailers using base_dn
                res = g.ldap.query(base_dn,"(&(o=%s)(objectclass=athenOrganisation))",data['o'],fields=["o"])
                if len(res) > 0:
                    raise AthenError("organisation already exists", "o", data)
                data['nonce'] = make_nonce()
                latex_data = {k:latexise(v) for k, v in data.items()}
                #send_mail("New Organisation",render_template_string(mail_text_template,**data),make_dvi(render_template_string(mail_latex_template,**latex_data)))
                data['objectclass'] = ['athenOrganisation','organization']
                data["status"] = 'P'
        if typ == "user":
            org_dn = mailer_dn.add("o",clean_string(request.form["o"]))
            new_dn = org_dn.add("cn",data['givenName']+" "+data['sn'])
            if mode == "new":
                data['objectclass'] = ['athenPerson','inetOrgPerson','organizationalPerson', 'person']
                # check if exists: but only in this org
                res = g.ldap.query(org_dn,"(&(cn=%s %s)(objectclass=athenPerson))",data["givenName"],data["sn"],fields=['cn'])
                if len(res) > 0:
                    raise AthenError("user already exists",None)
                data['cn'] = data['givenName']+' '+data['sn']
                data["status"] = "C"
        if mode == "new":
            data['timeCreated'] = data['timeLastUsed']
            g.ldap.add(new_dn, data)
        elif mode == "edit":
            g.ldap.modify(new_dn, data)
        else:
            raise AthenError("Unknown mode {}".format(mode),None)
        return ("OK", 200, {"Content-Type": "text/plain"})
    except:
        # log the exception
        app.logger.exception("exception in api()")
        # but don't tell the user anything useful
        return ("ERR", 500, {"Content-Type": "text/plain"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/rationale.html")
def rationale():
    return render_template("rationale.html")


@app.route('/org/confirm',methods=["GET","POST"])
def confirmorg():
    if request.method == "POST":
        nonce = request.form.get('nonce','')
        if len(nonce) != 10:
            flash("Key is not valid")
        else:
            try:
                get_ldap()
                nonce = nonce.upper()
                res = g.ldap.search(config.base_dn,"(&(objectclass=athenOrganisation)(nonce=%s))",nonce,fields=['o'])
                if len(res) == 0:
                    flash("Key is not valid")
                else:
                    res = res[0]
                    g.ldap_modify(res['dn'],{'status':"C",'timeLastUsed':ldap_time()})
                    send_mail('Confirmed organisation',"{} has confirmed".format(res['o']))
                    flash("{} has been validated".format(res['o']))
            except AthenError as e:
                flash(e.err)
    return render_template("confirm.html")

@app.route('/recv_key',methods=["POST"])
def recvkey():
    """Receive a GnuPG key"""
    try:
        get_ldap()
        mailer_dn = calc_mxdomain(request)
        


if __name__ == '__main__':
    app.run(debug=True,ssl_context=('/home/ian/athen/hub/cgi-bin/server.crt','/home/ian/athen/hub/cgi-bin/private.key'))




