#!/usr/bin/python

"""
The web interface of the local ("leaf") ATHEN mailserver
"""
import sys, os, ldap
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


from flask import Flask, session, redirect, url_for, escape, request, render_template, g, flash

app = Flask(__name__)

sys.path.append('../../lib')
from util import *
import config
import user
import submit


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
        g.ldap = LDAP(local=True,password=config.password)
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
    s = org['mail']
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
        # check if exists
        res = g.ldap.query(config.base_dn,"(&(o=%s)(objectclass=athenOrganisation))",data['o'],fields=["o"])
        if len(res) > 0:
            raise AthenError('Organisation of that name already exists',"o",data)
        submit.upload(data,'new','org',app.logger)
        data['userPassword'] = request.form['userPassword']
        if data['userPassword'] != request.form['userPassword_repeat']:
            raise AthenError('Passwords do not match','userPassword_repeat',data)
        if len(data['userPassword']) < 6:
            raise AthenError("Password must be at least 6 characters","userPassword",data)
        data['userPassword'] = create_new_hash(data['userPassword'])
        get_ldap()
        new_dn = config.base_dn.add("o",data["o"])
        check_mail(data)
        data['status'] = "P" # provisional
        data['timeCreated'] = data['timeLastUsed'] = ldap_time()
        data['objectclass'] = ['organization','athenOrganisation']
        g.ldap.add(new_dn,data)
        flash('New organisation saved successfully')
        return redirect(url_for('index'))
    except AthenError as e:
        flash(e.err)
        return render_template('editorg.html',mode='new',error_field=e.field,data=e.data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        get_ldap()
        org = request.form["username"]
        u = useer.User()
        if u.login(org,request.form['password']):
            session['user'] = u
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
    res = g.ldap.quiery(session['user'].dn)[0]
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
        submit.upload(data,'edit','org',app.logger)
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

if __name__ == '__main__':
    app.run(debug=True)




