#!/bin/sh
set +x
# the main startup script, sets up config files then runs supervisord
# This file is part of ATHEN.
# ATHEN is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# ATHEN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with ATHEN.  If not, see <http://www.gnu.org/licenses/>.


if [ ! -t 0 ] ; then
    echo No terminal so cannot do setup >&2
    exit 1
fi
apt-get -y update
DEBIAN_FRONTEND=noninteractive apt-get -y install apache2 dovecot-imapd dovecot-ldap libpam-script python-ldap debconf-utils roundcube roundcube-mysql- roundcube-sqlite3 slapd ldap-utils python-m2crypto python-ldap python-flask libapache2-mod-wsgi apache2-utils
cat ./debconf.keys | debconf-set-selections
DEBIAN_FRONTEND=noninteractive apt-get -y install postfix postfix-ldap 

# install our LDAP schema from hub
ldapadd -Y EXTERNAL -H ldapi:/// -f ../hub/athen.ldif

DIR=`dirname $0`

cp -R etc/* /etc/


if [ ! -h /var/lib/roundcube/plugins/athen ]; then
    ln -s $DIR/roundcube /var/lib/roundcube/plugins/athen
fi

if [ ! -h /usr/share/libpam-script/pam_script_auth ] ; then
    ln -s $DIR/adm/pam_script_auth /usr/share/libpam-script/pam_script_auth
fi
if [ ! -h /usr/share/libpam-script/pam_script_acct ] ; then
    ln -s $DIR/adm/pam_script_acct /usr/share/libpam-script/pam_script_acct
fi

#/usr/sbin/a2enmod ssl ; /usr/sbin/a2ensite default-ssl
cp -f /etc/services /var/spool/postfix/etc/services
cp -f /etc/resolv.conf /var/spool/postfix/etc

if [ ! -d /home/athen ] ; then
    groupadd -g 2002 athen ; useradd -g 2002 -m -u 2002 -s /bin/bash athen
    groupadd -g 2001 vmail ; useradd -g 2001 -m -u 2001 -s /bin/bash vmail
fi


# set some specific permissions for dovecot LDA logging
touch /var/log/dovecot-lda-errors.log
chgrp vmail /var/log/dovecot-lda-errors.log
chmod g+w  /var/log/dovecot-lda-errors.log
touch /var/log/dovecot-lda.log
chgrp vmail /var/log/dovecot-lda.log
chmod g+w /var/log/dovecot-lda.log

cd ~athen
if [ ! -d spool ] ; then
    mkdir spool
    chgrp vmail spool
    chmod 770 spool
fi

if [ ! -r htpasswd ] ; then
    echo Setting administrator password
    htpasswd -c -B htpasswd admin
fi

if [ -r /etc/ssl/private/athen.key -a -r /etc/ssl/certs/athen.pem  ] ; then
    echo Certificates found
else
    echo Need to set up SSL certificates
    # generate self-signed certificate so we can run
    openssl req -x509 -sha256 -nodes -days 1070 -newkey rsa:2048 -keyout /etc/ssl/private/athen.key -out /etc/ssl/certs/athen.pem -outform PEM
    # and a CSR so we can get higher authorities to sign it too.
    openssl x509 -x509toreq -in /etc/ssl/certs/athen.pem -inform PEM -out ~athen/request.csr -signkey /etc/ssl/private/athen.key
    chown athen:athen ~athen/request.csr
    echo You have now generated SSL certificates plus a Certificate Signing Request
    echo has been created as ~athen/request.csr, this can be submitted to a Certificate
    echo Authority, the signed certificate returned should be saved as
    echo /etc/ssl/certs/athen.pem
fi

if [ ! -L /var/lib/dbconfig-common/sqlite3/roundcube/roundcube ] ; then
    echo Database is not a link
    if [ -f ~athen/roundcube.sqlite ] ; then
	# we have our own sqlite database, so delete the fresh one and link
	rm /var/lib/dbconfig-common/sqlite3/roundcube/roundcube
    else
	echo No database in ~athen
	# no database, so move the fresh one made by the roundcube installer
	mv /var/lib/dbconfig-common/sqlite3/roundcube/roundcube ~athen/roundcube.sqlite
    fi
    ln -s ~athen/roundcube.sqlite /var/lib/dbconfig-common/sqlite3/roundcube/roundcube
    chmod 777 ~athen
fi

# get hostname from SSL cert
HOSTNAME=`openssl x509 -in /etc/ssl/certs/athen.pem -noout -subject | sed -e 's:.*CN=\([^/]*\).*:\1:'`
echo $HOSTNAME
# and substitute it into the config files
find /etc/ -name '*.in' -print | while read file ; do
				     sed -e "s/HOSTNAME/$HOSTNAME/" $file > ${file%.in}
				 done

