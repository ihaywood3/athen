#!/bin/bash
set -eux
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

DIR=`dirname $0`
cd $DIR

if false; then

apt-get -y update
DEBIAN_FRONTEND=noninteractive apt-get -y install apache2 dovecot-imapd dovecot-ldap dovecot-lmtpd libpam-script python3-ldap3 debconf-utils roundcube roundcube-mysql- roundcube-sqlite3 ldap-utils python3-flask apache2 libapache2-mod-php python3-lxml python3-bs4 python3-waitress libpam-ldapd python3-dateutil wget git runit
cat ./debconf.keys | debconf-set-selections
apt-get -y install slapd # user will enter password
DEBIAN_FRONTEND=noninteractive apt-get -y install postfix postfix-ldap 

# FIXME: currently using compiled bleeding-edge gnupg and its python binding 'gpg' from offical GPGME
apt-get install automake debhelper dh-autoreconf gettext autopoint file ghostscript help2man libbz2-dev libcurl4-gnutls-dev libgnutls28-dev libldap2-dev libnpth0-dev libreadline-dev libsqlite3-dev libusb-dev pkg-config texinfo transfig zlib1g-dev swig libncurses5-dev python3-dev

cd ~
mkdir -p gnupg_builds
cd gnupg_builds

wget -c https://gnupg.org/ftp/gcrypt/gnupg/gnupg-2.2.1.tar.bz2
wget -c https://gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-1.27.tar.bz2
wget -c https://gnupg.org/ftp/gcrypt/libgcrypt/libgcrypt-1.8.1.tar.bz2
wget -c https://gnupg.org/ftp/gcrypt/libksba/libksba-1.3.5.tar.bz2
wget -c https://gnupg.org/ftp/gcrypt/libassuan/libassuan-2.4.3.tar.bz2
wget -c https://gnupg.org/ftp/gcrypt/pinentry/pinentry-1.0.0.tar.bz2
wget -c https://gnupg.org/ftp/gcrypt/gpgme/gpgme-1.9.0.tar.bz2

for i in libgpg-error-1.27 libassuan-2.4.3 libgcrypt-1.8.1 libksba-1.3.5 pinentry-1.0.0 gnupg-2.2.1 gpgme-1.9.0  ; do
    tar xvjf $i.tar.bz2
    cd $i
    ./configure
    make
    make install
    if [ -d lang/python ] ; then
	cd lang/python
	python3 setup.py install
    fi
    cd ..
done


git clone https://github.com/ihaywood3/pgp-mime
cd pgp-mime
python3 setup.py install
cd ..

cd $DIR

# compile the shim, try to make it small
gcc user-shim.c -s -O3 -o user-shim

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

if [ ! -h /usr/local/lib/athen ] ; then
    ln -s $DIR /usr/local/lib/athen
fi
#/usr/sbin/a2enmod ssl ; /usr/sbin/a2ensite default-ssl; php5enmod mcrypt

cp -f /etc/services /var/spool/postfix/etc/services
cp -f /etc/resolv.conf /var/spool/postfix/etc


if [ ! -d /home/athen ] ; then
    groupadd -g 2000 athenusers
    useradd -g 2000 -m -u 2001 -s /bin/bash athen
    useradd -g 2000 -m -u 2002 -s /bin/false vmail
fi

if [ ! -d /var/log/athen ] ; then
    mkdir /var/log/athen
    chown athen:vmail /var/log/athen
    chmod go+rw /var/log/athen/
fi

# set some specific permissions for dovecot LDA logging
touch /var/log/dovecot-lda-errors.log
chgrp athenusers /var/log/dovecot-lda-errors.log
chmod g+w  /var/log/dovecot-lda-errors.log
touch /var/log/dovecot-lda.log
chgrp athenusers /var/log/dovecot-lda.log
chmod g+w /var/log/dovecot-lda.log

# some directories for the powershell downloader to use
mkdir -p /var/log/athen/remote
chmod go+rw /var/log/athen/remote/
mkdir -p /var/run/athen
chmod go+rw /var/run/athen


mkdir ~athen/latex_output
chown athen:www-data ~athen/latex_output
chmod g+w ~/athen/latex_output

cd ~vmail
if [ ! -d spool ] ; then
    mkdir spool
    chown vmail:athenusers spool
    chmod 750 spool
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
    chown athen:athenusers ~athen/request.csr
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


# apache setup
a2enmod ssl
a2enmod proxy
a2ensite default-ssl


# install our LDAP schema
ldapadd -Y EXTERNAL -H ldapi:/// -f ./athen.ldif
# change LDAP config to our specifications
ldapmodify -Y EXTERNAL -H ldapi:/// -f config.ldif

fi

HOSTNAME=athen-test

LDAP_PASSWORD=$(dd if=/dev/urandom bs=1 count=20 | base32)
echo bindpw $LDAP_PASSWORD >> /etc/nslcd.conf

# stop the server
service slapd stop
# wipe LDAp files
rm -f /var/lib/ldap/*
# restore with our contents
cat ./base.ldif | sed -e "s/HOSTNAME/$HOSTNAME/;s:PASSWD:$(slappasswd -s $LDAP_PASSWORD):" | slapadd -n 1
chown -R openldap:openldap /var/lib/ldap/*
# and restart
service slapd start

