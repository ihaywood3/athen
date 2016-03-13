

# install requirements
# slapd will prompt for password, slapd username is "cn=admin,dc=nodomain"
apt-get install -y --force-yes --no-install-recommends slapd ldap-utils apache2 python supervisor texlive-latex-base cups-client python-m2crypto python-ldap python-flask
ldapadd -Y EXTERNAL -H ldapi:/// -f athen.ldif
ldapmodify -Y EXTERNAL -H ldapi:/// -f config.ldif 
ldapadd -x -D "cn=admin,dc=athen,dc=net,dc=au" -W -f base.ldif # will ask for password again here
cp athen.pem /etc/ssl/certs/
cp athen.key /etc/ssl/private/
chmod 400 /etc/ssl/private/athen.key
EXPOSE 80 389 443
CMD ["/usr/bin/supervisord"]
#ENTRYPOINT /bin/bash
