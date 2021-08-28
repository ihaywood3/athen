#!/usr/bin/python

# script for when leaf server wants to update IP address

import cgi, os, ldap


c = ldap.initialize('ldap://localhost/')
c.simple_bind_s('cn=Admin,dc=athen,dc=net,dc=au','password')


