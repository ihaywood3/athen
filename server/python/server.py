#!/usr/bin/python

"""
The web interface of the local ("leaf") ATHEN mailserver
"""
import sys, os, ldap3, stat, pdb, time, logging, subprocess, threading, pudb, collections, pwd
if __name__=='__main__':
    sys.path.append('../../lib')
from util import *
import config, myldap, control

# WARNING: somebody needs to set this up
root_controller = None

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
\\signature{ {{signature}} }
\\address{ {{originator }} }
\\begin{document}
\\begin{letter}{ {{title}} {{cn}} \\\\ {{street}} \\\\ {{l}} {{postalCode}} {{st}} }
\\opening{Dear {{opening}},}

Your organisation has been registered on {{ network_name }} using this postal address.

Your logon name is\\texttt{ {{uid}} }, and your registration code is\\texttt{ {{nonce}} }

To confirm your registration, please go to \\texttt{https://{{domain}} }, click on `Register' and enter in the code above.

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
        ('l', True, None, 'Town'),
        ('postalCode', True, '[0-9]{4}', 'postcode'),
        ('telephoneNumber', False, '[0-9 ]{8,10}', 'Telephone number'),
        ('facsimileTelephoneNumber', False, '[0-9 ]{8,10}', 'Fax number'),
        ('deliveryFormat', False, 'pit|pit-rtf|hl7-oru-ft|hl7-oru-rtf|hl7-ref-ft|hl7-ref-rtf', 'Preferred delivery format')
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
        ('deliveryFormat', False, 'pit|pit-rtf|hl7-oru-ft|hl7-oru-rtf|hl7-ref-ft|hl7-ref-rtf', 'Preferred delivery format')
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
    ldap = getattr(g, 'ldap', None)
    if ldap is None:
        ldap = g.ldap = myldap.LDAP(dn=config.ldap_user,password=config.password,default_base=config.base_dn)
        #g.remote = myldap.LDAP(host=config.public_hub,default_base=config.public_base_dn)  # LDAP connection to remote public server
    return ldap

#@app.teardown_appcontext
#def close_connection(exception):
#    ldap = getattr(g, 'ldap', None)
#    if ldap is not None:
#        ldap.close()

@app.route('/config/index')
def index():
    return render_template('index.html')

@app.route("/")
def base_index():
    return redirect(url_for("index"))

@app.route('/static/style.css')
def css(): # really only for testing, apache should serve this
    return flask.send_from_directory(os.path.join(app.root_path,'..','static'),'style.css',mimetype='text/css')

@app.route("/config/rationale.html")
def rationale():
    return render_template("rationale.html")


@app.route('/config/acct/search')
def searchacct():
    if request.args.get('key',None) is None:
        res = []
    else:
        get_ldap()
        res = g.ldap.query("(|(&(o=%s*)(objectclass=athenOrganisation))(&(cn=%s*)(objectclass=athenPerson)))",request.args['key'],request.args['key'],fields=['cn','objectclass','businessCategory','medicalSpecialty','o','status','l'])
        g.ldap.close()
    logging.debug(res)
    return render_template('searchacct.html',result=res)

@app.route('/config/acct/show')
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
    g.ldap.close()
    return render_template('showacct.html',acct=acct,users=users,org=org)

@app.route('/config/acct/new')
def newacct():
    allow_unencrypted_home = False
    if not config.public_registration:
        if not 'uid' in session:
            flash("not logged in")
            return redirect(url_for('index'))
        if not session['uid'] == config.owner:
            flash("not authorised")
            return redirect(url_for('index'))
        else:
            allow_unencrypted_home = True
    if request.args['type'] == "O":
        templ = "editorg.html"
    else:
        templ = "editperson.html"
    data = collections.defaultdict(lambda: "")
    return render_template(templ,mode='new',error_field="",
                           allow_unencrypted_home=allow_unencrypted_home,
                           data=data)

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
    """quick utility to run command and check produced a file"""
    retcode = subprocess.call(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if retcode != 0:
        raise AthenError("%r failed" % cmd)
    if not os.path.exists(outfile):
        raise AthenError("%r failed to produce file %s" % (cmd,outfile))

@app.route('/config/acct/save',methods=['POST'])
def saveacct():
    allow_unencrypted_home = False
    if not config.public_registration:
        if not 'uid' in session:
            flash("You must log in to access this page")
            return redirect(url_for('index'))
        if not session['uid'] == config.owner:
            flash("not authorised")
            return redirect(url_for('index'))
        else:
            allow_unencrypted_home = True
    try:
        templ = "editorg.html"
        if request.form['type'] == 'O': # we an org
            data = validate_fields(request,'new',schema['org'])
            data['cn'] = data['o']
            data['objectclass'] = ['athenOrganisation','posixAccount']
            if data['businessCategory'] == 'General Practice':
                title = "Practice Manager \\\\"
            else:
                title = "Manager IT Services \\\\ "
            opening = "Madam/Sir"
            namefield = "o"
            logging.debug("config.base_dn = %r" % config.base_dn)
            new_dn = config.base_dn.add("o",data["o"])
            logging.debug("new_dn = %r" % new_dn)
        else:
            # an independent person
            templ = "editperson.html"
            data = validate_fields(request,'new',schema['person'])
            data['cn'] = data['givenName']+" "+data['sn']
            data['objectclass'] = ['athenPerson','posixAccount']
            title = ""
            namefield = "sn"
            opening = data['cn']
            new_dn = config.base_dn.add("cn",data["cn"])
        uid = make_username(data['cn'])
        passwd = request.form['userPassword']
        if passwd != request.form['userPassword_repeat']:
            raise AthenError('Passwords do not match','userPassword_repeat',data)
        if len(passwd) < 6:
            raise AthenError("Password must be at least 6 characters","userPassword",data)
        encrypt_flag = "Y"
        if allow_unencrypted_home and request.form['encryptFlag'] == "no":
            encrypt_flag = "N"
        get_ldap()
        res = g.ldap.query("(uid=%s)",uid,fields=['uid'])
        if len(res) > 0:
            raise AthenError("User of similar name exists",namefield,data)
        data['mail'] = uid+"@"+config.domain
    except AthenError as e:
        flash(e.err)
        return render_template(templ,mode='new',error_field=e.field,data=e.data,allow_unencrypted_home=allow_unencrypted_home)
    # ok error-checking is done if we get here
    # NB this is a page fragment: no </body></html>
    fragment = render_template("progress.html",data=data)
    session['username'] = data['cn']
    session['uid'] = data['uid'] = uid
    # now this all gets a bit ugly: during the streaming we can't access the normal Flask context variables
    # so save to our own locals so we can do the slow stuff during the stream
    ldap_conn = g.ldap
    reload_url = url_for('save_completed')
    latex_data = data.copy()
    del latex_data['objectclass']
    latex_data = {k:latexise(v) for k, v in latex_data.items()}
    latex_data["title"] = title
    latex_data['nonce'] = data['nonce'] = make_nonce()
    latex_data['originator'] = config.letter_origin_address
    latex_data['domain'] = config.domain
    latex_data['signature'] = config.letter_signature
    latex_data['network_name'] = config.letter_network_name
    latex_data['opening'] = opening
    # we need to do the LaTeX letter rendering here, but actual LaTeX'ing and sending later
    latex_text = flask.render_template_string(mail_latex_template,**latex_data)
    debug_mode = (config.debug and request.form.get('_testing') == 'yes')
    data['userpassword'] = passwd # strange, only in a dict will this variable 'survive' into the generator below. others are fine.
    def create_page(): # an internal generator
        yield fragment
        try:
            with main_lock:
                uidNumber = ldap_conn.get_next_uid(config.public_base_dn)
                logging.debug("new uid is %s",uidNumber)
                if not debug_mode:
                    for n, msg in root_controller.run(["NEWUSER",uid,uidNumber,data["cn"],data["userpassword"],encrypt_flag,config.domain]):
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
                        fname = latex_data["uid"]+ext
                        if os.path.exists(fname):
                            os.unlink(fname)
                    os.chdir(oldcwd)
            yield "<script>\nsetProgress(95,\"Saving record in LDAP database\");\n</script>\n"
            data['status'] = "P" # provisional
            data['timeCreated'] = data['timeLastUsed'] = myldap.ldap_time()
            data['gidNumber'] = '2000'
            data['uidNumber'] = uidNumber
            data['homeDirectory'] = '/home/athen/home/'+uid
            data['loginShell'] = '/bin/false'
            data["userpassword"] = myldap.hash_password(data["userpassword"])
            ldap_conn.add(new_dn,data)
            ldap_conn.close()
            yield "<script>\nsetProgress(100,\"Completed\");\nwindow.location.href = \"{}\";</script>\n</body></html>\n".format(reload_url)
        except Exception as e:
            yield "<script>\nsetError(\"{}\");\n</script>\n</body></html>\n".format(cprotect(str(e)))
            logging.exception("in yielder")
    return flask.Response(create_page())

@app.route('/config/acct/save_completed')
def save_completed():
    user = require_login('index')
    if user.is_class("athenorganisation"):
        typ="O"
    else:
        typ="P"
    g.ldap.close()
    return render_template('createdacct.html',uid=uid,cn=user.cn,type=typ)

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

def get_acct(acct):
    """get the full DN and CN of the named acct
    we assume account has been created: this func either succeeds or throws an exception"""
    res = g.ldap.query("(uid=%s)",acct)
    if len(res) == 0:
        raise AthenError("Account {} not found".format(uid),"cn",{"cn":res[0].cn})
    if len(res) != 1:
        raise AthenError("Account {} has multiple LDAP entries WHICH SHOULD NEVER EVER HAPPEN".format(org),"cn",{"cn":res[0].cn})
    return res[0]

@app.route('/config/login', methods=['GET', 'POST'])
def login():
    path = 'index'
    try:
        path = request.form["path"]
    except: pass
    if request.method == 'POST':
        get_ldap()
        uid = request.form["username"]
        res = g.ldap.query("(uid=%s)",uid)
        if len(res) == 1:
            if g.ldap.login(res[0].dn,request.form['password']):
                session['uid'] = uid
                session['username'] = res[0]['cn'] # for display purposes only
                flash("Logged in successfully")
                g.ldap.close()
                return redirect(url_for(path))
        flash("Username or password incorrect")
    g.ldap.close()
    return render_template('login.html',path=path)

def require_login(path='index'):
    get_ldap()
    if not 'uid' in session:
        raise LoginRequiredError(path)
    user = get_acct(session['uid'])
    return user

@app.errorhandler(LoginRequiredError)
def login_required_error(err):
    flash("Login required for this page")
    return redirect(url_for('login',path=err.args[0]))

@app.route('/config/logout')
def logout():
    session.pop('uid',None)
    session.pop('username',None)
    flash('Logged out successfully')
    return redirect(url_for('index'))

@app.route('/config/acct/edit')
def editacct():
    user = require_login('editacct')
    if user.is_class("athenorganisation"):
        templ = "editorg.html"
    else:
        templ = "editperson.html"
    g.ldap.close()
    return render_template(templ,mode='edit',
                           allow_unencrypted_home=False, # this can never be changed post-hoc
                           error_field="",data=user)

@app.route('/config/acct/update',methods=['POST'])
def updateacct():
    try:
        user = require_login('/acct/update')
        if user.is_class("athenorganisation"):
            assert request.form['type'] == "O"
            s = schema["org"]
            typ = "O"
        else:
            assert request.form["type"] == 'P'
            s = schema["person"]
            typ = "P"
        data = validate_fields(request,'edit',s)
        if request.form.get("status_closed", "no") == "yes":
            data['status'] = 'X'
        data['timeLastUsed'] = myldap.ldap_time()
        g.ldap.modify(user.dn,data)
        flash("Record modified")
        g.ldap.close()
        return redirect(url_for("index"))
    except AthenError as e:
        flash(e.err)
        return render_template('editacct.html',mode='edit',type=typ,error_field=e.field,data=e.data)



@app.route('/config/user/new')
def newuser():
    require_login('newuser')
    return render_template("edituser.html",mode='new',error=None,data={})

@app.route('/config/user/edit')
def edituser():
    user = require_login('index')
    user_dn = user.dn.add("cn",request.args['cn'])
    logging.debug("user_dn %r",user_dn)
    res = g.ldap.query(base=user_dn)[0]
    logging.debug("res=%r",res)
    g.ldap.close()
    return render_template('edituser.html',mode='edit',data=res,the_dn=str(user_dn))


@app.route('/config/user/save',methods=['POST'])
def saveuser():
    try:
        org = require_login('newuser')
        if request.form["givenName"] == "":
            cn = request.form['sn']
        else:
            cn = request.form["givenName"]+" "+request.form['sn']
        data = validate_fields(request,'new',schema['employee'])
        user_dn = org.dn.add("cn",cn)
        res = g.ldap.query("(&(objectclass=athenPerson)(cn=%s))",cn,base=org.dn,fields=["cn"])
        if len(res) > 0:
            raise AthenError('user of same name exists','givenName',data)
        if 'mail' in data and data['mail'] != "":
            check_mail(data)
        else:
            # use same email as our master organisation
            data['mail'] = org['mail']
        data['timeCreated'] = data['timeLastUsed'] = myldap.ldap_time()
        data['objectclass'] = ['person','organizationalPerson','inetOrgPerson','athenPerson']
        data['status'] = 'C' # for Confirmed, as we are being entered directly by user
        g.ldap.add(user_dn,data)
        flash('New person saved successfully')
        g.ldap.close()
        return redirect(url_for('index'))
    except AthenError as e:
        flash(e.err)
        return render_template('edituser.html',mode='new',error_field=e.field,data=e.data)

@app.route('/config/user/update',methods=["POST"])
def updateuser():
    try:
        org = require_login('index')
        if request.form["givenName"] == "":
            cn = request.form['sn']
        else:
            cn = request.form["givenName"]+" "+request.form['sn']
        the_dn = org.dn.add("cn",cn)
        data = validate_fields(request,'edit',schema['employee'])
        res = g.ldap.query("(&(objectclass=athenPerson)(cn=%s))",cn,base=org.dn,fields=["cn"])
        if len(res) == 0:
            raise AthenError('User does not exist','givenName',data)
        if request.form.get("status_closed", "no") == "yes":
            data['status'] = 'X'
        #submit.upload(data,'edit','user',app.logger)
        data['timeLastUsed'] = myldap.ldap_time()
        g.ldap.modify(the_dn,data)
        flash('Person updated successfully')
        g.ldap.close()
        return redirect(url_for('index'))
    except AthenError as e:
        flash(e.err)
        return render_template('edituser.html',mode='edit',error_field=e.field,data=e.data)  


@app.route('/config/user/list')
def listusers():
    org = require_login('/user/list')
    res = g.ldap.query("(objectclass=athenPerson)",base=org.dn,fields=['cn',"sn","medicalSpecialty","givenName","providerNumber"])
    g.ldap.close()
    return render_template('listusers.html',users=res)

@app.route('/config/confirm',methods=["GET","POST"])
def confirmacct():
    if request.method == "POST":
        try:
            nonce = clean_string(request.form.get('nonce',''))
            nonce = nonce.upper()
            uid = clean_string(request.form['uid'])
            if len(nonce) != NONCELENGTH:
                raise AthenError("Key is an invalid length","nonce",{"nonce":nonce,'uid':uid})
            get_ldap()
            res = g.ldap.query("(uid=%s)",uid,fields=['nonce'],base=config.base_dn)
            if not res:
                raise AthenError("User ID is not valid","nonce",{"nonce":nonce,"uid":uid})
            if res[0]['nonce'] != nonce:
                raise AthenError("Key is not valid","nonce",{"nonce":nonce,"uid":uid})
            g.ldap.modify(res[0].dn,{'status':"C",'timeLastUsed':myldap.ldap_time()})
            if not config.debug:
                send_mail('Confirmed organisation',"{} has confirmed".format(uid))
            flash("Your account has been validated")
            g.ldap.close()
            return redirect(url_for('index'))
        except AthenError as e:
            flash(e.err)
            return render_template("confirm.html",error_field=e.field,data=e.data)
    else:
        data = {"nonce":"","uid":""}
        if "uid" in session:
            data['uid'] = session['uid']
        return render_template("confirm.html",error_field="",data=data)


if __name__ == '__main__':
    if config.debug:
        # use the internal toy webserver. use sudo for root access (needs to be passwordless)
        root_controller = control.RootController(debug=True)
        application.run(debug=True)
    else:
        # we are running For Real, as root
        root_controller = control.RootController()
        n = pwd.getpwnam("www-data")
        try: 
            os.mkdir(os.path.dirname(config.http_socket))
        except FileExistsError: pass
        os.chown(os.path.dirname(config.http_socket),n.pw_uid,n.pw_gid)
        # now drop privilege
        os.setgid(n.pw_gid)
        os.setuid(n.pw_uid)
        # and run the server
        import waitress
        waitress.serve(application,unix_socket=config.http_socket)
        
