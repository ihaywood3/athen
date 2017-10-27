#!/usr/bin/python3

"""
this is the main python delivery module for incoming mail
when called as a script, it is to be called
as the correct user (using user_shim generally) with the mail passed on
stdin, and sys.argv[1] = the destination user
both when the user is logged in or not

Also  used as a library when unspooling and sending
"""



import os, sys, os.path, email, smtplib, subprocess, email.generator, traceback, logging

import pgp_mime.parse

if os.path.exists("/home/ian/athen/lib"):
    sys.path.append("/home/ian/athen/lib")
else:
    sys.path.append("/usr/lib/athen/lib")

import util, dsn, pit, myldap, config, mailfilter # these modules shared between the client and server
import accounting, userdb


# global: if we are unspooling then generate DSN rather than reply on postfix to do it for us
generate_dsn = False

#!/usr/bin/python3
# this is the main python delivery script



import os, sys

import myldap, config, util # these modules shared between the client and server


class NoSuchUser(util.AthenError): pass

def get_user_context(user=None):
    """
    look up user in the ATHEN LDAP database
    $HOME, $USER etc environment variables are set

    The actual process uid needs to be set before this point 
    """
    if user is None:
        set_env = False # don't set envionment because we are using it
        user = os.environ['USER']
    else:
        set_env = True
        
    with myldap.LDAP(dn=config.ldap_user,password=config.password,default_base=config.base_dn) as ldap:
        res = ldap.query("(&(objectclass=posixAccount)(uid=%s))",user,fields=["uidNumber","homeDirectory",'gidNumber','cn','deliveryFormat','deliveryMethod'])
        if len(res) == 0:
            raise NoSuchUser("no such user in LDAP:"+user,data="5.2.1")


        # give us a minimally sane environment
        user_context = {}
        user_content['UID'] = int(res[0].uidNumber) # pure efficiency: os.getuid() would always work
        if os.getuid() != user_context['UID']:
            raise util.AthenError("LDAP uid is {} system user id is {}".format(res[0].uidNumber, os.getuid()),data="5.2.1")
        user_context["HOME"] = res[0].homeDirectory
        user_context["USER"] = user
        user_context["REALNAME"] = res[0].cn
        
        if old_lang: os.environ["LANG"] = old_lang
        user_context["GID"] = res[0].gidNumber
        user_context['deliveryFormat'] = res[0],get_field('deliveryFormat',[],True)
        user_context['deliveryMethod'] = res[0].get_field('deliverymethod',None)

        if set_env:
            try:
                old_lang = os.environ["LANG"]
            except:
                old_lang = None
            # because security: clear the environment
            os.environ.clear()
            for e in ['USER',"HOME","REALNAME"]:
                os.environ[e] = user_context[e]
            os.environ['LOGNAME'] = user_context['USER']
            os.environ["PATH"] = "/bin:/usr/bin"
        return user_context


class DovecotDeath(util.AthenError):
    pass


def startup():
    """common startup code for ail-handling scripts
    sets user context and parses messgae on stdin
    """
    global uctx
    user = sys.argv[1]
    uctx = get_user_context(user)
    msg = email.message_from_binary_file(sys.stdin.buffer)
    emaildir = os.path.join(uctx["HOME"],"mail")
    if not os.access(emaildir,os.X_OK):
        # we are not logged in
        raise util.AthenError("directory {} not available".format(emaildir),data="4.2.1")
    return (uctx, msg)

def postfix_deliver(msg,want_dsn=False):
    smtp = smtplib.SMTP("127.0.0.1")
    smtp.starttls()
    if want_dsn:
        smtp.send_message(msg,rcpt_options=["NOTIFY=SUCCESS,FAILURE,DELAY"])
    else:
        smtp.send_message(msg)
    smtp.close()

def dovecot_deliver(uctx,msg,box="INBOX"):
    pro = subprocess.Popen(["/usr/lib/dovecot/deliver","-d",uctx["USER"],"-f",msg['From'],'-m',box,'-e'],stdin=subprocess.PIPE)
    g = email.generator.BytesGenerator(pro.stdin)
    g.flatten(msg)
    pro.stdin.close()
    logging.debug("Dovecot delivery from '{}' to '{}' subject '{}' id '{}'".format(msg['From'],msg['To'],msg['Subject'],msg['Message-Id']))
    try:
        pro.wait(120)
    except:
        pro.kill()
        raise util.AthenError("Dovecot process failed to finish in 120 sec",data="5.2.0")
    if pro.returncode != 0:
        raise DovecotDeath("Dovecot died",data=pro.returncode)

def do_delivery(uctx, msg):
    with gpg.Context(armor=True) as ctx:
        msg = pgp_mime.parse.parse(msg,ctx=ctx)
        # log the message
        # may get "gobbled" at this stage if it's a delivery notification email
        backward, box, onward = accounting.received_filter(msg)
        if backward:
            postfix_deliver(backward)
        if onward:
            # do medical attachment magic
            udb = userdb.UserDB()
            onward = mailfilter.process(uctx, onward, udb)
            # add pass to dovecot for actual delivery to mailbox on disc
            dovecot_deliver(uctx,onward, box)

if __name__=='__main__':

    try:
        if sys.argv[2] == '--unspool': # ../adm/unspool-mail.sh is calling us
            generate_dsn = True
        do_delivery(*startup())
    except DovecotDeath as e:
        if generate_dsn:
            ret = dsn.prepare_dsn_report(msg,action='failed',
                                         diagnostic="Dovecot process failed with error {}".format(e.data),
                                         status="5.2.0")
            postfix_deliver(ret)
        else:
            sys.exit(e.data)
    except util.AthenError as e:
        if generate_dsn:
            ret = dsn.prepare_dsn_report(msg,action='failed',
                                         diagnostic=e.err,
                                         status=e.data)
            postfix_deliver(ret)
        sys.stderr.write(e.data+" "+e.err+"\n")
        s = e.data.split(".")
        if s[0] == "4":
            sys.exit(util.EX_TEMPFAIL)
        else:
            sys.exit(util.EX_SOFTWARE)
    except:
        sys.stderr.write("5.3.0 Internal error\n")
        sys.stderr.write(traceback.format_exc())
        sys.exit(util.EX_SOFTWARE)
