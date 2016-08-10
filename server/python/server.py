#!/usr/bin/python

"""
The web interface of the local ("leaf") ATHEN mailserver
"""
import sys, os, ldap, stat, pdb, time, logging
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


from flask import session, redirect, url_for, escape, request, render_template, g, flash
import flask

app = flask.Flask(__name__)

sys.path.append('../../lib')
from util import *
import config, store, submit, myldap, control


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

Your logon name is\\texttt{ {{uid}} }, and registration code is\\texttt{ {{nonce}} }

To confirm your registration, please go to \\texttt{https://athen.org/}, click on `Register' and enter in the code above.

If you did not request registration, plase check if someone in your organisation did register and show them this letter.

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
        ],
    "user": [
            ('givenName', True, None, 'Given name'),
            ('sn',True, None, 'Surname'),
            ('medicalSpecialty', True, None, 'Profession/medical specialty'),
            ('mail', False, '^[A-Za-z0-9._%+-]+$', "Username"),
            ('providerNumber', False, '^[0-9]{5,6}[0-9A-Z][A-Z]$', "Medicare provider number")
            ]
    }

def set_controller(rc):
    global root_controller
    root_controller = rc

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
    return render_template('editorg.html',mode='new',error_field="",data={})


@app.context_processor
def select_context():
    def html_select(options,value):
        s = ""
        for i in options:
            if i == value:
                s += "<option selected>{}</option>\n".format(i)
            else:
                s += "<option>{}</option>\n".format(i)
        return s
    return dict(html_select=html_select)

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
    except AthenError as e:
        flash(e.err)
        return render_template('editorg.html',mode='new',error_field=e.field,data=e.data)
    # ok error-checking is done if we get here
    # this all gets a bit ugly: during the streaming we can't access the normal Flask context variables
    # so save to our own locals so we can do the slow stuff during the stream
    # this is a page fragment: no </body></html>
    fragment = render_template("progress.html",data=data)
    cookie = store.make_cookie()
    session['code'] = cookie
    session['username'] = data['o']
    reload_url = url_for('save_completed')
    ldap_conn = g.ldap
    latex_data = {k:latexise(v) for k, v in data.items()}
    nonce = make_nonce()
    latex_data['nonce'] = nonce
    latex_data['uid'] = uid
    # we need to do rendering here, but actual LaTeX'ing and sending later
    latex_text = flask.render_template_string(mail_latex_template,**latex_data)
    debug_mode = (app.config["TESTING"] and request.form['testing'] == 'yes')
    data['passwd'] = passwd # strange, only in a dict will this variable 'survive' into the generator below. others are fine.
    def create_page(): # an internal generator
        yield fragment
        try:
            if not debug_mode:
                for n, msg in root_controller.run(["NEWUSER",uid,data["o"],data["passwd"]]):
                    yield "<script>\nsetProgress({},\"{}\");\n</script>\n".format(n,cprotect(msg))
            yield "<script>\nsetProgress(90,\"Saving record in SQL database\");\n</script>\n"
            passwd = create_new_hash(data.pop('passwd'))
            u.add(nonce,1,passwd)
            u.set_cookie(cookie)
            with open(os.path.join(config.latex_path,latex_data['uid']+".tex"),"w") as f:
                f.write(latex_text)
            yield "<script>\nsetProgress(95,\"Saving record in LDAP database\");\n</script>\n"
            data['status'] = "P" # provisional
            data['timeCreated'] = data['timeLastUsed'] = myldap.ldap_time()
            data['objectclass'] = ['organization','athenOrganisation']
            ldap_conn.add(new_dn,data)
            yield "<script>\nsetProgress(100,\"Completed\");\nwindow.location.href = \"{}\";</script>\n</body></html>\n".format(reload_url)
        except Exception as e:
            yield "<script>\nsetError(\"{}\");\n</script>\n</body></html>\n".format(cprotect(str(e)))
    return flask.Response(create_page())

@app.route('/org/save_completed')
def save_completed():
    u, dn, org = require_login('index')
    return render_template('createdorg.html',uid=u.uid,orgname=org)

@app.route("/testyield",methods=["GET"])
def test_yield():
    start_fragment = """<html><body>
    <p><progress id="created_progress" max=10 value=1></p>
<p><span id="desc"></span></p>
<p><span id="error_text"></span></p>
<script>
function setProgress(n,msg)
{
    var bar = document.getElementById("created_progress");
    var desc = document.getElementById("desc");
 
    bar.value = n;
    desc.innerHTML= msg;
}
</script>
    """
    def yielder():
        yield start_fragment
        for i in range(1,11):
            time.sleep(3)
            yield "\n<script>\nsetProgress({0},\"Step {0}\");\n</script>\n".format(i)
        yield "</body></html>"
    return flask.Response(yielder())
        
    

def get_org_dn(org):
    """get the full DN of the named organisation
    assumed org has been created: succeed or throw an exception"""
    mail = org+"@"+config.domain
    res = g.ldap.query(config.base_dn,"(&(mail=%s)(objectclass=athenOrganisation))",mail,fields=["o"])
    if len(res) == 0:
        raise AthenError("Organisation {} not found".format(org),"o",{"o":org})
    if len(res) != 1:
        raise AthenError("Organisation {} has multiple LDAP entries WHICH SHOULD NEVER HAPPEN".format(org),"o",{"o":org})
    return (res[0].dn, res[0]['o'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    path = 'index'
    try:
        path = request.form["path"]
    except: pass
    if request.method == 'POST':
        get_ldap()
        org = request.form["username"]
        u = store.User(org)
        if u.login(request.form['password']):
            session['code'] = u.cookie
            _, orgname = get_org_dn(org)
            session['username'] = orgname # for display purposes only
            flash("Logged in successfully")
            return redirect(url_for(path))
        else:
            flash("Organisation/password incorrect")
    return render_template('login.html',path=path)

def require_login(path='index'):
    get_ldap()
    if not 'code' in session:
        raise LoginRequiredError(path)
    u = store.get_user_by_cookie(session['code'])
    if u is None:
        raise LoginRequiredError(path)
    dn, orgname = get_org_dn(u.uid)
    return (u, dn, orgname)

@app.errorhandler(LoginRequiredError)
def login_required_error(err):
    flash("Login required for this page")
    return redirect(url_for('login',path=err.args[0]))

@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    u = store.get_user_by_cookie(session['code'])
    u.logout()
    session.pop('code',None)
    session.pop('username',None)
    flash('Logged out successfully')
    return redirect(url_for('index'))

@app.route('/org/edit')
def editorg():
    if not 'code' in session:
        flash("You must log in for this page")
        return redirect(url_for('login',path='/org/edit/'))
    get_ldap()
    u = store.get_user_by_cookie(session['code'])
    if u is None:
        flash("You must log in for this page")
        return redirect(url_for('login',path='/org/edit/'))       
    mail = org+"@"+config.domain
    res = g.ldap.query(config.base_dn,"(&(mail=%s)(objectclass=athenOrganisation))",mail)
    return render_template('editorg.html',mode='edit',error_field="",data=res[0])

@app.route('/org/update',methods=['POST'])
def updateorg():
    try:
        u, dn, orgname = require_login('/org/update')
        data = validate_fields(request,'edit',schema['org'])
        if request.form.get("status_closed", "no") == "yes":
            data['status'] = 'X'
        #submit.upload(data,'edit','org',app.logger)
        data['timeLastUsed'] = myldap.ldap_time()
        g.ldap.modify(dn,data)
        flash("Organisation record modified")
        return redirect(url_for("index"))
    except AthenError as e:
        flash(e.err)
        return render_template('editorg.html',mode='edit',error_field=e.field,data=e.data)



@app.route('/user/new')
def newuser():
    require_login('/user/new')
    return render_template("edituser.html",mode='new',error=None,data={})

@app.route('/user/edit')
def edituser():
    u, dn, orgname = require_login('index')
    the_dn = dn.add("cn",request.args['cn'])
    res = g.ldap.query(the_dn)[0]
    return render_template('edituser.html',mode='edit',data=res,the_dn=str(the_dn))


@app.route('/user/save',methods=['POST'])
def saveuser():
    try:
        u, org_dn, orgname = require_login('/user/new')
        if request.form["givenName"] == "":
            cn = request.form['sn']
        else:
            cn = request.form["givenName"]+" "+request.form['sn']
        data = validate_fields(request,'new',schema['user'])
        the_dn = org_dn.add("cn",cn)
        res = g.ldap.query(org_dn,"(&(objectclass=athenPerson)(cn=%s))",cn,fields=["cn"])
        if len(res) > 0:
            raise AthenError('user of same name exists','givenName',data)
        if 'mail' in data and data['mail'] != "":
            check_mail(data)
        else:
            # use same email as our master organisation
            res = g.ldap.query(org_dn,fields=["mail"])
            data['mail'] = res[0]['mail']
        #submit.upload(data,'new','user',app.logger)
        data['timeCreated'] = data['timeLastUsed'] = myldap.ldap_time()
        data['objectclass'] = ['person','organizationalPerson','inetOrgPerson','athenPerson']
        data['status'] = 'A' # for Active, as we are being entered directly by user
        g.ldap.add(the_dn,data)
        flash('New person saved successfully')
        return redirect(url_for('index'))
    except AthenError as e:
        flash(e.err)
        return render_template('edituser.html',mode='new',error_field=e.field,data=e.data)

@app.route('/user/update',methods=["POST"])
def updateuser():
    try:
        u, org_dn, orgname = require_login('index')
        if request.form["givenName"] == "":
            cn = request.form['sn']
        else:
            cn = request.form["givenName"]+" "+request.form['sn']
        the_dn = org_dn.add("cn",cn)
        res = g.ldap.query(org_dn,"(&(objectclass=athenPerson)(cn=%s))",cn,fields=["cn"])
        if len(res) == 0:
            raise AthenError('User does not exist','givenName',data)
        data = validate_fields(request,'edit',schema['user'])
        #submit.upload(data,'edit','user',app.logger)
        data['timeLastUsed'] = myldap.ldap_time()
        g.ldap.modify(the_dn,data)
        flash('Person updated successfully')
        return redirect(url_for('index'))
    except AthenError as e:
        flash(e.err)
        return render_template('edituser.html',mode='edit',error_field=e.field,data=e.data)  


@app.route('/user/list')
def listusers():
    u, org_dn, orgname = require_login('/user/list')
    res = g.ldap.query(dn,"(objectclass=athenPerson}",fields=['cn',"sn","medicalSpecialty","givenName","providerNumber"])
    return render_template('listusers.html',users=res)

@app.route('/org/confirm',methods=["GET","POST"])
def confirmorg():
    if request.method == "POST":
        try: 
            nonce = clean_string(request.form.get('nonce',''))
            org = clean_string(request.form.get('o',''))
            if org == '': raise AthenError("Organisation required","o",{})
            if len(nonce) != NONCELENGTH: raise AthenError("Key is not valid","nonce",{"nonce":nonce,"o":org})
            nonce = nonce.upper()
            u = store.User(make_username(org))
            if nonce != u.get('nonce'): raise AthenError("Key is not valid","nonce",{"o":org})
            get_ldap()
            the_dn, org_name = get_org_dn(u.uid)
            g.ldap.modify(the_dn,{'status':"C",'timeLastUsed':myldap.ldap_time()})
            if not app.config['TESTING']:
                send_mail('Confirmed organisation',"{} has confirmed".format(org_name))
            flash("{} has been validated".format(org_name))
        except AthenError as e:
            flash(e.err)
    return render_template("confirm.html")


if __name__ == '__main__':
    # this is for testing mode
    # proper running from control.py
    store.init_db(debug=True,sql_path="/home/ian/athen/test.db")
    root_controller = control.RootController(debug=True)
    app.secret_key = config.secret_key
    app.run(debug=True)




