#!/bin/sh
# install requirements
# slapd will prompt for password, slapd username is "cn=admin,dc=nodomain"
set +x
set +e
apt-get install -y --no-install-recommends slapd ldap-utils apache2 python texlive-latex-base cups-client python-m2crypto python-ldap python-flask libapache2-mod-wsgi
ldapadd -Y EXTERNAL -H ldapi:/// -f athen.ldif
ldapmodify -Y EXTERNAL -H ldapi:/// -f config.ldif 
ldapadd -x -D "cn=admin,dc=athen,dc=net,dc=au" -W -f base.ldif # will ask for password again here
openssl req -new -newkey rsa:2048 -days 1070 -nodes -x509 -keyout private.key -out server.crt
#cp athen.pem /etc/ssl/certs/
#cp athen.key /etc/ssl/private/
#chmod 400 /etc/ssl/private/athen.key

