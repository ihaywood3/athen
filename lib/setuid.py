#!/usr/bin/python3
# this is the main python delivery script

"""
do a setuid() from Python
There's no (reliable, secure) way to do this from shell
"""


import os, sys

import myldap, config, util # these modules shared between the client and server


class NoSuchUser(util.AthenError): pass

def setuid(user):
    """
    look up user in the ATHEN LDAP database, and then use
    os.setuid() to become that user.
    $HOME, $USER and $UID environment variables are set

    This function must be run as root to work
    """

    with myldap.LDAP(dn=config.ldap_user,password=config.password,default_base=config.base_dn) as ldap:
        res = ldap.query("(&(objectclass=posixAccount)(uid=%s))",user,fields=["uidNumber","homeDirectory",'gidNumber','cn','deliveryFormat'])
        if len(res) == 0:
            raise NoSuchUser("no such user in LDAP:"+user,data="5.2.1")

        try:
            old_lang = os.environ["LANG"]
        except:
            old_lang = None
        # because security: clear the environment
        os.environ.clear()
        # There's No Going Back, root privilege permanently lost here
        os.setgid(int(res[0].gidNumber))
        os.setuid(int(res[0].uidNumber)) 

        # give us a minimally sane environment
        user_context = {}
        user_context["UID"] = os.environ['UID'] = res[0].uidNumber 
        user_context["HOME"] = os.environ['HOME'] = res[0].homeDirectory
        user_context["USER"] = os.environ['USER'] = os.environ["LOGNAME"] = user
        user_context["REALNAME"] = os.environ['REALNAME'] = res[0].cn
        os.environ["PATH"] = "/bin:/usr/bin"
        if old_lang: os.environ["LANG"] = old_lang
        user_context["GID"] = res[0].gidNumber
        if res[0].has_key("deliveryFormat"):
            user_context['deliveryFormat'] = res[0].deliveryFormat
        else:
            user_context['deliveryFormat'] = []
        return user_context
