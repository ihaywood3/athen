#!/usr/bin/python

# general HTTP interface to our LDAP index server

import ldap, ldap.filter
import hashlib, binascii, os, re, random, os.path, sys, smtplib, email, email.utils, time
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import email.utils

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

SWEARWORDS = ['SHIT', 'FUCK', 'CUNT', 'TWAT']

DEFAULT_TO= "ian@haywood.id.au"
DEFAULT_FROM="ldap@athen.net.au"
DEFAULT_SERVER="haywood.id.au"


from flask import Flask, session, redirect, url_for, escape, request

app = Flask(__name__)

base_dn = 'dc=athen,dc=net,dc=au'
org_fields = ['o','l','st','businessCategory','street','postalCode','telephoneNumber','facsimileTelephoneNumber','userPassword','mail','status']


def send_mail(subject, text, dvi=None):
    msg = MIMEMultipart(
        From=DEFAULT_FROM,
        To=DEFAULT_TO,
        Date=email.utils.formatdate(localtime=True),
        Subject=subject
    )
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
    smtp.sendmail(send_from, [DEFAULT_TO], msg.as_string())
    smtp.close()

def make_dvi(latex):
    fd, tmpf = tempfile.mkstemp(".tex")
    tmpf_dvi = tmpf[:-3]+'dvi' 
    os.write(fd, latex)
    os.close(fd)
    os.chdir(os.path.dirname(tmpf))
    os.system("latex {}".format(tmpf))
    with open(tempf_dvi,'r') as f:
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

    
def ldap_time():
    return time.strftime("%Y%m%d%H%M%SZ",time.gmtime())

def get_ldap():
    """Opens a new LDAP connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'ldap'):
        g.ldap = ldap.initialize('ldap://localhost/')
        g.ldap.simple_bind_s('cn=Admin,dc=athen,dc=net,dc=au','password')
    return g.ldap


def ldap_query(base_dn,query,fields,args=None,scope=ldap.SCOPE_SUBTREE,dn_args=None):
    if not dn_args is None:
        base_dn = ldap.filter.filter_format(base_dn,dn_args)
    if not args is None:
        query = ldap.filter.filter_format(query,args)
    res = g.ldap.search-s(base_dn,scope,query,fields)
    return [fold_dn(i) for i in res]

def e(x,*args):
    return ldap.filter.filter_format(x,args)

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
    salt = fields[2]
    reps = int(fields[3])*10000
    dk = hashlib.pbkdf2_hmac(algo_names[algo],bytes(password),binascii.unhexlify(salt),reps)
    h = binascii.hexlify(dk)
    return "$"+str(algo)+"$"+str(reps)+"$"+salt+"$"+h+"$"

def create_new_hash(password):
    return make_hash(password,"$1$20$"+make_salt())

def clean_string(s):
    """Remove LDAP-sensitive chars from a string"""
    translation_table = dict.fromkeys(map(ord, '!@#(){}%^&*|=+\n\r\t";:<>,'), None)
    return s.translate(translation_table)


def fold_dn(i):
    dn, vals = i
    vals = {k: v[0] for k, v in vals}
    vals['dn'] = dn
    return vals


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/org/search')
def searchorg():
    if request.args.get('key',None) is None:
        res = []
    else:
        get_ldap()
        res = g.ldap.search_s(base_dn, ldap.SCOPE_SUBTREE, ldap.filter.filter_format("(&(o=%s*)(objectclass=athenOrganization))",[request.args.get('key', '')]),['o','l','st','businessCategory'])
        res = [fold_dn(i) for i in res] # fold the DNs in the dict to make it a bit easier to work with
    return render_template('searchorg.html',result=res)

@app.route('/org/show')
def showorg():
    get_ldap()
    the_dn = ldap.filter.filter_format("o=%s,",[request.args['o']])+base_dn
    org = ldap_query(the_dn,"(objectclass=athenOrganization)",scope=ldap.SCOPE_BASE)
    users = ldap_query(the_dn,"(objectclass=athenPerson)")
    return render_template('showorg.html',org=org,users=users)

@app.route('/org/new'):
def neworg():
    vals = {i: "" for i in org_fields}
    vals['error'] = ""
    vals['error_field'] = ""
    vals['mode'] = 'new'
    return render_template('editorg.html',**vals)

def load_from_form(fieldslist):
    vals = {}
    for f in fieldslist:
        val = clean_string(request.form[f])
        if val != "":
            vals[f] = val
    return vals

def org_fields_validate(vals):
    vals['error'] = None
    if "o" in vals:
        if len(vals["o"]) < 4:
            vals['error_field'] = "o"
            vals['error'] = "Organisation name is too short"
    if "l" in vals:
        if len(vals["l"]) < 3:
            vals['error_field'] = "l"
            vals['error'] = "Suburb name is too short"
    if "street" in vals:
        if len(vals["street"]) < 3:
            vals['error_field'] = "street"
            vals['error'] = "Street name is too short"
    if "postalCode" in vals:
        m = re.match("^[0-9]{4}$",vals['postalCode'])
        if not m:
            vals['error_field'] = 'postalCode'
            vals['error'] = "Postcode must be four digits"
    if "telephoneNumber" in vals:
        vals['telephoneNumber'] = re.sub("[^0-9]", "", vals['telephoneNumber'])
        m = re.match("^[0-9]{7,10}$",vals['telphoneNumber'])
        if not m:
            vals['error_field'] = 'telphoneNumber'
            vals['error'] = "telephone number must be 7 to 10 digits"
    if "facsimileTelephoneNumber" in vals:
        vals['facsimileTelephoneNumber'] = re.sub("[^0-9]", "", vals['facsimileTelephoneNumber'])
        m = re.match("^[0-9]{7,10}$",vals['facsimileTelphoneNumber'])
        if not m:
            vals['error_field'] = 'facsimileTelphoneNumber'
            vals['error'] = "fax number must be 7 to 10 digits"
    return vals

@app.route('/org/save')
def neworg():
    vals = load_from_form(org_fields[:-1})
    vals['mode'] = 'new'
    for f in ['o','l','street','telephoneNumber','postalCode','userPassword','userPassword_repeat']:
        if not f in vals:
            vals['error_field'] = f
            if f == 'o': f = "organisation name"
            if f == 'l': f = "suburb"
            vals["error"] = f+" is required"
            return render_template('neworg.html',**vals)
    if vals['userPassword'] != vals['userPassword_repeat']:
        vals['error_field'] = 'userPassword_repeat'
        vals['error'] = "passwords do not match"
        return render_template('editorg.html',**vals)
    if len(vals['userPassword']) < 6:
        vals["error"] = "password must be at least 6 characters"
        vals["error_field"] = "userPassword"
        return render_template('editorg.html',**vals)
    vals = org_fields_validate(vals)
    if vals['error'] is None:
        vals['userPassword'] = create_new_hash(vals['userPassword'])
        vals['nonce'] = make_nonce()
        send_mail("New Organisation",render_template('invite.txt',**vals),make_dvi(render_template('invite.tex',**vals)))
        get_ldap()
        new_dn = e("o=%s,",vals['o'])+base_dn)
        # check if exists
        res = g.ldap.search_s(new_dn,ldap.SCOPE_BASE,"{objectclass=athenOrganization)",["o"])
        if len(res) > 0:
            vals['error'] = 'Organisation of that name already exists'
            val['error_field'] = "o"
            del vals["nonce"]
            return render_template('editorg.html',**vals)
        vals['status'] = "P" # provisional
        vals['timeCreated'] = vals['timeLastUsed'] = ldap_time()
        if 'mode' in vals: del vals['mode']
        if 'error' in vals: del vals['error']
        modlist = [(k,[v]) for k, v in vals.items()]
        modlist.append(('objectclass',['organization','athenOrganization']))
        g.ldap.add_s(new_dn,modlist)
        flash('New organisation saved successfully')
        return redirect(url_for('index'))
    else:
        return render_template('neworg.html',**vals)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        get_ldap()
        org = request.form["o"]
        the_dn = e("o=%s,",org)+base_dn
        res = g.ldap.search_s(the_dn,ldap.SCOPE_BASE,"{objectclass=athenOrganization)",["o","userPassword"])
        if len(res) == 0:
            flash("Organisation/password incorrect")
        else:
            ldap_passwd  = res[0][1]['userPassword'][0]
            entered_password = request.form['password']
            hashed_password = make_hash(entered_password,ldap_password)
            if hashed_password != ldap_password:
                flash("Organisation/password incorrect")
            else:
                session['the_dn'] = the_dn
                flash("Logged in successfully")
                return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('the_dn', None)
    return redirect(url_for('index'))

@app.route('/org/edit'):
def editorg():
    if not 'the_dn' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    get_ldap()
    the_dn = session['the_dn']
    res = g.ldap.search_s(the_dn,ldap.SCOPE_BASE,"{objectclass=athenOrganization)",org_fields)
    if len(res) == 0: # shouldn't ever happen really
        flash('No such organisation')
        return redirect(url_for('index'))
    vals = fold_dn(res[0])
    vals['error'] = ""
    vals['error_field'] = ""
    vals['mode'] = 'edit'
    return render_template('editorg.html',**vals)

@app.route('/org/update')
def updateorg():
    if not 'the_dn' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    vals = load_from_form(org_fields[:-1])
    vals['mode'] = 'edit'
    if "status_closed" in vals and vals["status_closed"] = "yes":
        del vals['status_closed']
        vals['status'] = 'X'
    vals = org_fields_validate(vals)
    if not vals['error'] is None:
        return render_template('neworg.html',**vals)
    get_ldap()
    del vals['mode']
    del vals['error']
    modlist = [(ldap.MOD_REPLACE,k,[v]) for k, v in vals.items()]
    g.ldap.modify_s(session['the_dn'],modlist)
    flash("Organisation record modified")
    return redirect(url_for("index"))

@app.route('/org/confirm',methods=["GET","POST"])
def confirmorg():
    if request.method == "POST":
        nonce = request.form.get('nonce','')
        if len(nonce) != 10:
            flash("Key is not valid")
        else:
            get_ldap()
            nonce = nonce.upper()
            res = g.ldap.search_s(base_dn,ldap.SCOPE_SUBTREE,e("(&(objectclass=athenOrganisation)(nonce=%s))",nonce),['o'])
            if len(res) == 0:
                flash("Key is not valid")
            else:
                the_dn = res[0][0]
                g.ldap_modify_s(the_dn,[(ldap.MOD_REPLACE,'status',['C'])])
                send_mail('Confirmed organisation',"{} has confirmed".format(res[0][1]['o'][0]))
                flash("%s has been validated" % res[0][1]['o'][0])
    return render_template("confirm.html")
    


user_fields = ['givenName','sn','medicalSpecialty','providerNumber']

@app.route('/user/new')
def newuser():
    if not 'the_dn' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))                    
    return render_template("edituser.html",mode='new',error=None,givenName='',sn='',medicalSpecialty='',providerNumber='')

@app.route('/user/edit')
def edituser():
    if not 'the_dn' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))get_ldap()
    the_dn = e("cn=%s,",request.args['cn'])+session['the_dn']
    res = ldap_query(the_dn,"(objectclass=athenPerson)",user_fields,scope=ldap.SCOPE_BASE)
    vals = res[0]
    vals['error'] = None
    vals['mode'] = 'edit'
    return render_template('edituser.html',**vals)

def validate_user(vals):
    # FIXME: do provider number validation here
    pass


@app.route('/user/save')
def newuser():
    if not 'the_dn' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    get_ldap()
    if request.form["givenName"] == "":
        cn = request.form['sn']
    else:
        cn = request.form["givenName"]+" "+request.form['sn']
    vals = load_from_form(user_fields)
    vals['cn'] = cn
    vals['mode'] = 'new'
    validate_user(vals)
    if not 'medicalSpecialty' in vals or not vals['medicalSpecialty']:
        vals['error'] = 'medical specialty is required'
        vals['error_field'] = 'medicalSpecialty'
    if len(cn) < 2:
        vals['error'] = 'Need surname at least'
        vals['error_field'] = 'sn'
    the_dn = e("cn=%s,",cn)+session['the_dn']
    org_dn = session['the_dn']
    res = ldap_query(the_dn,"(objectclass=athenPerson)",["cn"],scope=ldap.SCOPE_BASE)
    if len(res) > 0:
        vals['error'] = 'user of same name exists'
        vals['error_field'] = 'givenName'
    if vals['error']:
        return render_template('edituser.html',**vals)
    res = ldap_query(org_dn,"(objectclass=athenOrganisation",["mail"],scope=ldap.SCOPE_BASE)
    vals['mail'] = res[0]['mail']
    vals['timeCreated'] = vals['timeLastUsed'] = ldap_time()
    if 'mode' in vals: del vals['mode']
    if 'error' in vals: del vals['error']
    modlist = [(k,[v]) for k, v in vals.items()]
    modlist.append(('objectclass',['person','organizationalPerson','inetOrgPerson','athenPerson']))
    g.ldap.add_s(the_dn,modlist)
    flash('New person saved successfully')
    return redirect(url_for('index'))

@app.route('/user/update')
def saveuser():
    if not 'the_dn' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    get_ldap()
    vals['mode'] = 'edit'
    cn = request.form["givenName"]+" "+request.form['sn']
    vals = load_from_form(user_fields)
    the_dn = e("cn=%s,",cn)+session['the_dn']
    org_dn = session['the_dn']
    res = ldap_query(the_dn,"(objectclass=athenPerson)",["cn"],scope=ldap.SCOPE_BASE)
    if len(res) == 0:
        vals['error'] = 'No such user exists'
        vals['error_field'] = 'givenName'
        return render_template('edituser.html',**vals)
    validate_user(vals)
    if vals['error']:
        return render_template('edituser.html',**vals)
    vals['timeLastUsed'] = ldap_time()
    if 'mode' in vals: del vals['mode']
    if 'error' in vals: del vals['error']
    modlist = [(k,[v]) for k, v in vals.items()]
    g.ldap.modify_s(the_dn,modlist)
    flash('Person updated successfully')
    return redirect(url_for('index'))

@app.route('user/list')
def listusers():
    if not 'the_dn' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    get_ldap()
    res = ldap_query(the_dn,"(objectclass=athenPerson}",['cn',"sn","medicalSpecialty","givenName"])
    return render_template('listusers.html',users=res)

if __name__ == '__main__':
    app.run(debug=True)



