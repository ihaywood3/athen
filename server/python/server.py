#!/usr/bin/python

"""
The web interface of the local ("leaf") ATHEN mailserver
"""
import sys, os, ldap, stat, pdb, time, logging, subprocess, threading
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

sys.path.append(__location__+'/../../lib')
from util import *
import config, myldap, control

# get the root controller started before we get anywhere near Flask
root_controller = control.RootController(debug=config.debug)

from flask import session, redirect, url_for, escape, request, render_template, g, flash
import flask

main_lock = threading.Lock() # a lock for creating new users, system stuff is very much one-at-a-time
application = flask.Flask(__name__)
app = application
application.secret_key = config.secret_key

mail_text_template ="""
Organisation Name: {{cn}}
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
\\begin{letter}{ {{title}}} {{cn}} \\\\ {{street}} \\\\ {{l}} {{postalCode}} {{st}} }
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
    "person": [ # an "independent user, ie./ not part of an organisation"
        ('st', True, None, 'State'),
        ('l', True, None, 'Town'),
        ('street', True, None, 'Street'),
        ('postalCode', True, '[0-9]{4}', 'postcode'),
        ('telephoneNumber', False, '[0-9 ]{8,10}', 'Telephone number'),
        ('facsimileTelephoneNumber', False, '[0-9 ]{8,10}', 'Fax number'),
        ('givenName', True, None, 'Given name'),
        ('sn',True, None, 'Surname'),
        ('medicalSpecialty', True, None, 'Profession/medical specialty'),
        #("ahpra", False, None, "AHPRA registration number"),
        ('providerNumber', False, '^[0-9]{5,6}[0-9A-Z][A-Z]$', "Medicare provider number")
    ],
    "employee": [ # someone working for an org but may not have an account in their own right
        ('givenName', True, None, 'Given name'),
        ('sn',True, None, 'Surname'),
        ('medicalSpecialty', True, None, 'Profession/medical specialty'),
        #("ahpra", False, None, "AHPRA registration number"),
        ('providerNumber', False, '^[0-9]{5,6}[0-9A-Z][A-Z]$', "Medicare provider number")
    ]
    }

def get_ldap():
    """Opens a new LDAP connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'ldap'):
        g.ldap = myldap.LDAP(dn=config.ldap_user,password=config.password,default_base=config.base_dn)
        #g.remote = myldap.LDAP(host=config.public_hub,default_base=config.public_base_dn)  # LDAP connection to remote public server
    return g.ldap
    

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/rationale.html")
def rationale():
    return render_template("rationale.html")


@app.route('/acct/search')
def searchacct():
    if request.args.get('key',None) is None:
        res = []
    else:
        get_ldap()
        res = g.ldap.query("(|(&(o=%s*)(objectclass=athenOrganisation))(&(cn=%s*)(objectclass=athenPerson)))",request.args['key'],request.args['key'],fields=['cn','objectclass'])
    return render_template('searchacct.html',result=res)

@app.route('/acct/show')
def showacct():
    get_ldap()
    the_dn = request.args['dn']
    acct = g.ldap.query(base=the_dn)[0]
    org = acct.is_class('athenorganisation')
    if org:
        users = g.ldap.query("(objectclass=athenPerson)",base=the_dn)
    else:
        users = []
    s = acct.get_field("mail")
    if acct['status'] == 'X':
        s = "invalid"
    s = s.replace("@"," at ")
    acct['displayEmail'] = s
    return render_template('showacct.html',acct=acct,users=users,org=org)

@app.route('/acct/new')
def newacct():
    if not config.public_registration:
        if not 'uid' in session:
            return redirect(url_for('index'))
        if not session['uid'] == config.owner:
            flash("not authorised")
            return redirect(url_for('index'))
    return render_template('editacct.html',mode='new',error_field="",data={})


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

def cmd_check(cmd,outfile):
    """quck utility to run command and check produced a file"""
    retcode = subprocess.call(cmd)
    if retcode != 0:
        raise AthenError("%r failed" % cmd)
    if not os.path.exists(outfile):
        raise AthenError("%r failed to produce file %s" % (cmd,outfile))

@app.route('/acct/save',methods=['POST'])
def saveacct():
    if not config.public_registration:
        if not 'user' in session:
            flash("You must log in to access this page")
            return redirect(url_for('index'))
        if not session['user'].owner:
            flash("not authorised")
            return redirect(url_for('index'))
    try:
        if request.form['type'] == 'O': # we an org
            data = validate_fields(request,'new',schema['org'])
            uid = make_username(data['o'])
            data['cn'] = data['o']
            new_dn = config.base_dn.add("o",data["o"])
            data['objectclass'] = ['athenOrganisation','posixAccount']
            title = "Manager IT Services \\\\ "
            namefield = "o"
        else:
            # an independent person
            data = validate_fields(request,'new',schema['person'])
            data['cn'] = data['givenName']+" "+data['sn']
            uid = make_username(data['cn'])
            new_dn = config.base_dn.add("cn",data["cn"])
            data['objectclass'] = ['athenPerson','posixAccount']
            title = ""
            namefield = "sn"
        passwd = request.form['userPassword']
        if passwd != request.form['userPassword_repeat']:
            raise AthenError('Passwords do not match','userPassword_repeat',data)
        if len(passwd) < 6:
            raise AthenError("Password must be at least 6 characters","userPassword",data)
        get_ldap()
        res = g.ldap.query(config.base_dn,"(uid=%s)",uid,fields=['uid'])
        if len(res) > 0:
            raise AthenError("User of similar name exists",namefield,data)
        data['mail'] = uid+"@"+config.domain
    except AthenError as e:
        flash(e.err)
        return render_template('editacct.html',mode='new',error_field=e.field,data=e.data)
    # ok error-checking is done if we get here
    # this all gets a bit ugly: during the streaming we can't access the normal Flask context variables
    # so save to our own locals so we can do the slow stuff during the stream
    # this is a page fragment: no </body></html>
    fragment = render_template("progress.html",data=data)
    session['username'] = data['cn']
    session['uid'] = uid
    reload_url = url_for('save_completed')
    ldap_conn = g.ldap
    latex_data = {k:latexise(v) for k, v in data.items()}
    latex_data["title"] = title
    latex_data['nonce'] = data['nonce'] = make_nonce()
    # we need to do rendering here, but actual LaTeX'ing and sending later
    latex_text = flask.render_template_string(mail_latex_template,**latex_data)
    debug_mode = (request.form['testing'] == 'yes' or config.debug)
    data['userpassword'] = passwd # strange, only in a dict will this variable 'survive' into the generator below. others are fine.
    def create_page(): # an internal generator
        yield fragment
        try:
            with main_lock:
                if not debug_mode:
                    for n, msg in root_controller.run(["NEWUSER",uid,data["cn"],data["userpassword"]]):
                        yield "<script>\nsetProgress({},\"{}\");\n</script>\n".format(n,cprotect(msg))
                yield "<script>\nsetProgress(90,\"Creating confirmation letter\");\n</script>\n"
                oldcwd = os.getcwd()
                os.chdir(config.latex_path)
                try:
                    lname, dviname, psname = [latex_data['uid']+i for i in [".tex",".dvi",".ps"]]
                    with open(lname,"w") as f:
                        f.write(latex_text)
                    cmd_check(["/usr/bin/latex",lname],dviname)
                    cmd_check(["/usr/bin/dvips",dviname,"-o",psname],psname)
                    # FIXME:  somehow send PS to the print queue here
                finally:
                    for ext in [".tex",".dvi",".aux",".log"]:
                        fname = latex_data{"uid"]+ext
                        if os.path.exists(fname):
                            os.unlink(fname)
                    os.chdir(oldcwd)
            yield "<script>\nsetProgress(95,\"Saving record in LDAP database\");\n</script>\n"
            data['status'] = "P" # provisional
            data['timeCreated'] = data['timeLastUsed'] = myldap.ldap_time()
            data['gidNumber'] = '200'
            data['uidNumber'] = ldap_conn.get_next_uid()
            data['homeDirectory'] = '/home/athen/home/'+uid
            data["userpassword"] = myldap.make_hash(data{"userpassword"])
            ldap_conn.add(new_dn,data)
            yield "<script>\nsetProgress(100,\"Completed\");\nwindow.location.href = \"{}\";</script>\n</body></html>\n".format(reload_url)
        except Exception as e:
            yield "<script>\nsetError(\"{}\");\n</script>\n</body></html>\n".format(cprotect(str(e)))
    return flask.Response(create_page())

@app.route('/org/save_completed')
def save_completed():
    uid, dn, cn = require_login('index')
    return render_template('createdacct.html',uid=uid,cn=cn)

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

def get_acct_dn(acct):
    """get the full DN and CN of the named acct
    assumed org has been created: succeed or throw an exception"""
    res = g.ldap.query("(uid=%s)",uid,fields=["cn"])
    if len(res) == 0:
        raise AthenError("Account {} not found".format(uid),"o",{"o":cn})
    if len(res) != 1:
        raise AthenError("Account {} has multiple LDAP entries WHICH SHOULD NEVER HAPPEN".format(org),"o",{"o":org})
    return (res[0].dn, res[0]['cn'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    path = 'index'
    try:
        path = request.form["path"]
    except: pass
    if request.method == 'POST':
        get_ldap()
        uid = request.form["username"]
        res = g.ldap.query("(uid=%s)",uid,fields=["cn"])
        if len(res) == 1:
            if g.ldap.login(res[0].dn,request.form['password']):
                session['uid'] = uid
                session['username'] = res[0]['cn'] # for display purposes only
                flash("Logged in successfully")
                return redirect(url_for(path))
        flash("Username or password incorrect")
    return render_template('login.html',path=path)

def require_login(path='index'):
    get_ldap()
    if not 'uid' in session:
        raise LoginRequiredError(path)
    dn, name = get_acct_dn(session['uid'])
    return (session['uid'], dn, name)

@app.errorhandler(LoginRequiredError)
def login_required_error(err):
    flash("Login required for this page")
    return redirect(url_for('login',path=err.args[0]))

@app.route('/logout')
def logout():
    session.pop('uid',None)
    session.pop('username',None)
    flash('Logged out successfully')
    return redirect(url_for('index'))

@app.route('/acct/edit')
def editacct():
    _, dn, _ = require_login('/acct/edit')
    res = g.ldap.query(base=dn)[0]
    return render_template('editacct.html',mode='edit',error_field="",data=res)

@app.route('/acct/update',methods=['POST'])
def updateacct():
    try:
        uid, dn, cn = require_login('/acct/update')
        res = g.ldap.query(base=dn)[0]
        if res.is_class("athenorganisation"):
            s = schema["org"]
        else:
            s = schema["person"]
        data = validate_fields(request,'edit',s)
        if request.form.get("status_closed", "no") == "yes":
            data['status'] = 'X'
        data['timeLastUsed'] = myldap.ldap_time()
        g.ldap.modify(dn,data)
        flash("Record modified")
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
    user_dn = dn.add("cn",request.args['cn'])
    res = g.ldap.query(base=user_dn)[0]
    return render_template('edituser.html',mode='edit',data=res,the_dn=str(user_dn))


@app.route('/user/save',methods=['POST'])
def saveuser():
    try:
        u, org_dn, orgname = require_login('/user/new')
        if request.form["givenName"] == "":
            cn = request.form['sn']
        else:
            cn = request.form["givenName"]+" "+request.form['sn']
        data = validate_fields(request,'new',schema['employee'])
        user_dn = org_dn.add("cn",cn)
        res = g.ldap.query(org_dn,"(&(objectclass=athenPerson)(cn=%s))",cn,fields=["cn"])
        if len(res) > 0:
            raise AthenError('user of same name exists','givenName',data)
        if 'mail' in data and data['mail'] != "":
            check_mail(data)
        else:
            # use same email as our master organisation
            res = g.ldap.query(base=org_dn,fields=["mail"])
            data['mail'] = res[0]['mail']
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
        data = validate_fields(request,'edit',schema['employee'])
        res = g.ldap.query(org_dn,"(&(objectclass=athenPerson)(cn=%s))",cn,fields=["cn"])
        if len(res) == 0:
            raise AthenError('User does not exist','givenName',data)
        if request.form.get("status_closed", "no") == "yes":
            data['status'] = 'X'
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
    res = g.ldap.query("(objectclass=athenPerson}",base=dn,fields=['cn',"sn","medicalSpecialty","givenName","providerNumber"])
    return render_template('listusers.html',users=res)

@app.route('/acct/confirm',methods=["GET","POST"])
def confirmacct():
    if request.method == "POST":
        try:
            u, dn, cn = require_login('index')
            nonce = clean_string(request.form.get('nonce',''))
            nonce = nonce.upper()
            if len(nonce) != NONCELENGTH:
                raise AthenError("Key is not valid","nonce",{"nonce":nonce})
            get_ldap()
            res = g.ldap.query(base=dn,fields['nonce'])[0]
            if res['nonce'] != nonce:
                raise AthenError("Key is not valid","nonce",{"nonce":nonce})
            g.ldap.modify(dn,{'status':"C",'timeLastUsed':myldap.ldap_time()})
            if not app.config['TESTING']:
                send_mail('Confirmed organisation',"{} has confirmed".format(cn))
            flash("Your account has been validated")
            return redirect(url_for('index'))
        except AthenError as e:
            flash(e.err)
            return render_template("confirm.html",error_field=e.field,data=e.data)
    else:
        return render_template("confirm.html",error_field="",data={"nonce":""})


if __name__ == '__main__':
    # this is for testing mode
    # proper running via application object
    application.run(debug=config.debug)
