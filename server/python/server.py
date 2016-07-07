#!/usr/bin/python

"""
The web interface of the local ("leaf") ATHEN mailserver
"""
import sys, os, ldap
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


from flask import Flask, session, redirect, url_for, escape, request, render_template, g, flash, render_template_string

app = Flask(__name__)

sys.path.append('../../lib')
from util import *
import config, store, submit, myldap


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

Your registration code is\\texttt{ {{nonce}} }

If you wish to register, please go to \\texttt{https://athen.org/}, click on `Register' and enter in the code above.

If you did not request registration, plase check if someone in your organisation did register and ask them for more details.

If you still have no idea what this letter is about, please contact me on the above address.

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
            ('mail', True, '^[A-Za-z0-9._%+-]+$', "Username")
        ],
    "user": [
            ('givenName', True, None, 'Given name'),
            ('sn',True, None, 'Surname'),
            ('medicalSpecialty', True, None, 'Profession/medical specialty'),
            ('mail', False, '^[A-Za-z0-9._%+-]+$', "Username"),
            ('providerNumber', False, '^[0-9]{5,6}[0-9A-Z][A-Z]$', "Medicare provider number")
            ]
    }

def get_ldap():
    """Opens a new LDAP connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'ldap'):
        g.ldap = myldap.LDAP(local=True,password=config.password)
        #g.remote = LDAP()  # LDAP connection to remote public server
    return g.ldap


def check_mail(data):
    email = data['mail']+'@'+config.domain
    res = g.ldap.query(config.base_dn,"(mail=%s)",email)
    if len(res) > 0:
        raise AthenError('Username already in use for this mailserver','mail',data)
    data['mail'] = email

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/rationale.html")
def rationale():
    return render_template("rationale.html")


@app.route('/org/search')
def searchorg():
    if request.args.get('key',None) is None:
        res = []
    else:
        get_ldap()
        res = g.ldap.query(config.base_dn, "(&(o=%s*)(objectclass=athenOrganisation))",request.args['key'],fields=['o','l','st','businessCategory'])
    return render_template('searchorg.html',result=res)

@app.route('/org/show')
def showorg():
    get_ldap()
    the_dn = config.base_dn.add("o",request.args['o'])
    org = g.ldap.query(the_dn,"(objectclass=athenOrganisation)",node=True)[0]
    users = g.ldap.query(the_dn,"(objectclass=athenPerson)")
    s = org.mail
    if org['status'] == 'X':
        s = "invalid"
    s = s.replace("@"," at ")
    org['displayEmail'] = s
    return render_template('showorg.html',org=org,users=users)

@app.route('/org/new')
def neworg():
    if not config.public_registration:
        if not 'user' in session:
            flash("You must log in to access this page")
            return redirect(url_for('index'))
        if not session['user'].owner:
            flash("not authorised")
            return redirect(url_for('index'))       
    return render_template('editorg.html',mode='new',error_field="",data=emptydict())

def send_to_shell_daemon(uid,passwd,org):
    # we know uid and org won't have | in them, password might so last
    passwd = passwd.replace("P","P1")
    passwd = passwd.replace("|","P0")
    cmd = "NEWUSER|{}|{}|{}\n".format(uid,org,passwd)
    with open("/tmp/athen.control.fifo","w") as f:
        f.write(cmd)

@app.route('/org/save',methods=['GET','POST'])
def saveorg():
    if not config.public_registration:
        if not 'user' in session:
            flash("You must log in to access this page")
            return redirect(url_for('index'))
        if not session['user'].owner:
            flash("not authorised")
            return redirect(url_for('index'))  
    try:
        data = validate_fields(request,'new',schema['org'])
        #submit.upload(data,'new','org',app.logger)
        passwd = request.form['userPassword']
        if passwd != request.form['userPassword_repeat']:
            raise AthenError('Passwords do not match','userPassword_repeat',data)
        if len(passwd) < 6:
            raise AthenError("Password must be at least 6 characters","userPassword",data)
        uid = make_username(data['o'])
        u = store.User(uid)
        if u.user_exists():
            raise AthenError("Organisation of similar name exists","o",data)
        get_ldap()
        new_dn = config.base_dn.add("o",data["o"])
        data['mail'] = uid+"@"+config.domain
        # check if exists
        res = g.ldap.query(config.base_dn,"(&(|(o=%s)(mail=%s))(objectclass=athenOrganisation))",data['o'],data['mail'],fields=["o"])
        if len(res) > 0:
            raise AthenError('Organisation of that name already exists',"o",data)
        # ok error-checking is done if we get here
        send_to_shell_daemon(uid,passwd,data["o"])
        passwd = create_new_hash(passwd)
        nonce = make_nonce()
        u.add(nonce,1,passwd)
        latex_data = {k:latexise(v) for k, v in data.items()}
        latex_data['nonce'] = nonce
        send_mail("New Organisation",render_template_string(mail_text_template,**data),make_dvi(render_template_string(mail_latex_template,**latex_data)))
        data['status'] = "P" # provisional
        data['timeCreated'] = data['timeLastUsed'] = myldap.ldap_time()
        data['objectclass'] = ['organization','athenOrganisation']
        g.ldap.add(new_dn,data)
        flash('New organisation saved successfully')
        return redirect(url_for('index'))
    except AthenError as e:
        flash(e.err)
        return render_template('editorg.html',mode='new',error_field=e.field,data=e.data)

def get_org_dn(org):
    """get the full DN of the named organisation
    assumed org has been created: succeed or throw an exception"""
    res = g.ldap.query(config.base_dn,"(&(o=%s)(objectclass=athenOrganisation))",data['o'],fields=["o"])
    if len(res) == 0:
        raise AthenError("Organisation {} not found".format(org),"o",{"o":org})
    if len(res) != 1:
        raise AthenError("Organisation {} has multiple LDAP entries WHICH SHOULD NEVER HAPPEN".format(org),"o",{"o":org})
    return res[0]['dn']

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        get_ldap()
        org = request.form["username"]
        u = store.User(org)
        if u.login(org,request.form['password']):
            session['user'] = u
            u.dn = get_org_dn(org)
            flash("Logged in successfully")
            return redirect(url_for('index'))
        else:
            flash("Organisation/password incorrect")
    return render_template('login.html')

@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('user', None)
    flash('Logged out successfully')
    return redirect(url_for('index'))

@app.route('/org/edit')
def editorg():
    if not 'user' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    get_ldap()
    res = g.ldap.query(session['user'].dn)[0]
    return render_template('editorg.html',mode='edit',error_field="",data=res)

@app.route('/org/update',methods=['POST'])
def updateorg():
    if not 'user' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    try:
        get_ldap()
        data = validate_fields(request,'edit',schema['org'])
        if request.form.get("status_closed", "no") == "yes":
            data['status'] = 'X'
        #submit.upload(data,'edit','org',app.logger)
        data['timeLastUsed'] = ldap_time()
        g.ldap.modify(session['user'].dn,data)
        flash("Organisation record modified")
        return redirect(url_for("index"))
    except AthenError as e:
        flash(e.err)
        return render_template('editorg.html',mode='edit',error_field=e.field,data=e.data)



@app.route('/user/new')
def newuser():
    if not 'user' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))                    
    return render_template("edituser.html",mode='new',error=None,data=emptydict())

@app.route('/user/edit')
def edituser():
    if not 'user' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    get_ldap()
    the_dn = session['user'].dn.add("cn",request.args['cn'])
    res = g.ldap.query(the_dn)[0]
    return render_template('edituser.html',mode='edit',data=res,the_dn=str(the_dn))


@app.route('/user/save')
def saveuser():
    if not 'user' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    try:
        get_ldap()
        if request.form["givenName"] == "":
            cn = request.form['sn']
        else:
            cn = request.form["givenName"]+" "+request.form['sn']
        data = validate_fields(request,'new',schema['user'])
        the_dn = session['user'].dn.add("cn",cn)
        org_dn = session['user'].dn
        res = g.ldap.query(org_dn,"(&(objectclass=athenPerson)(cn=%s)",cn,fields=["cn"])
        if len(res) > 0:
            raise AthenError('user of same name exists','givenName',data)
        if 'mail' in data and data['mail'] != "":
            check_mail(data)
        else:
            # use same email as our master organisation
            res = g.ldap.query(org_dn,fields=["mail"])
            data['mail'] = res['mail']
        submit.upload(data,'new','user',app.logger)
        data['timeCreated'] = data['timeLastUsed'] = ldap_time()
        data['objectclass'] = ['person','organizationalPerson','inetOrgPerson','athenPerson']
        g.ldap.add(the_dn,data)
        flash('New person saved successfully')
        return redirect(url_for('index'))
    except AthenError as e:
        flash(e.err)
        return render_template('edituser.html',mode='new',error_field=e.field,data=e.data)

@app.route('/user/update')
def updateuser():
    if not 'the_dn' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    try:
        get_ldap()
        if request.form["givenName"] == "":
            cn = request.form['sn']
        else:
            cn = request.form["givenName"]+" "+request.form['sn']  
        the_dn = session['user'].dn.add("cn",cn)
        org_dn = session['user'].dn
        res = g.ldap.query(org_dn,"(&(objectclass=athenPerson)(cn=%s)",cn,fields=["cn"])
        if len(res) == 0:
            raise AthenError('User does not exist','givenName',data)
        submit.upload(data,'edit','user',app.logger)
        data['timeLastUsed'] = ldap_time()
        g.ldap.modify(the_dn,data)
        flash('Person updated successfully')
        return redirect(url_for('index'))
    except AthenError as e:
        flash(e.err)
        return render_template('edituser.html',mode='edit',error_field=e.field,data=e.data)  


@app.route('/user/list')
def listusers():
    if not 'user' in session:
        flash("You must log in for this page")
        return redirect(url_for('login'))
    get_ldap()
    res = g.ldap.query(session['user'].dn,"(objectclass=athenPerson}",fields=['cn',"sn","medicalSpecialty","givenName","providerNumber"])
    return render_template('listusers.html',users=res)

@app.route('/org/confirm',methods=["GET","POST"])
def confirmorg():
    if request.method == "POST":
        try: 
            nonce = clean_string(request.form.get('nonce',''))
            org = clean_string(request.form.get('o',''))
            if org == '': raise AthenError("Organisation required","o",{})
            if len(nonce) != 10: raise AthenError("Key is not valid","nonce",{"nonce":nonce,"o":org})
            nonce = nonce.upper()
            u = store.User(make_username(org))
            if nonce != u.get('nonce'): raise AthenError("Key is not valid","nonce",{"o":org})
            get_ldap()
            the_dn = get_org_dn(org)
            g.ldap_modify(the_dn,{'status':"C",'timeLastUsed':ldap_time()})
            send_mail('Confirmed organisation',"{} has confirmed".format(org))
            flash("{} has been validated".format(org))
        except AthenError as e:
            flash(e.err)
    return render_template("confirm.html")


if __name__ == '__main__':
    store.init_db(debug=False)
    app.run(debug=False)




