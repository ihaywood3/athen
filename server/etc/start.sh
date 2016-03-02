#!/bin/bash

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




ready_for_config () {
    if [ ! -t 0 ] ; then
	echo No terminal so cannot do setup, please re-run docker with -i -t options >&2
	exit 1
    fi

}


# main logic

if [ ! -d /data/ ] ; then
   echo Directory /data/ does not exist >&2
   exit 1
fi

<<<<<<< HEAD
if [ -r /data/passwd.bak -a /data/passwd.bak -nt /etc/passwd ] ; then
    cp /data/passwd.bak /etc/passwd
fi

if [ ! -d /data/spool ] ; then
    mkdir /data/spool
    chgrp vmail /data/spool
    chmod 770 /data/spool
fi

=======
>>>>>>> 4cd1bd19cb47a08274b0afedb732e72e48e7cc24
if [ ! -r /data/htpasswd ] ; then
    echo Setting administrator password
    htpasswd -c -B /data/htpasswd admin
fi

if [ -r /data/private.key -a -r /data/certificate.pem  ] ; then
    echo Certificates found
else
    echo Need to set up SSL certificates
    ready_for_config
    cd /data/
    # generate self-signed certificate so we can run
    openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout private.key -out certificate.pem -outform PEM
    # and a CSR so we can get higher authorities to sign it too.
    openssl x509 -x509toreq -in certificate.pem -inform PEM -out request.csr -signkey private.key
    echo You have now generated SSL certificates plus a Certificate Signing Request
    echo has been created as /data/request.csr, this can be submitted to a Certificate
    echo Authority, the signed certificate returned should be saved as
    echo /data/certificate.pem
fi

if [ ! -L /var/lib/dbconfig-common/sqlite3/roundcube/roundcube ] ; then
    echo Database is not a link
    if [ -f /data/roundcube.sqlite ] ; then
	# we have our own sqlite database, so delete the fresh one and link
	rm /var/lib/dbconfig-common/sqlite3/roundcube/roundcube
    else
	echo No database in /data
	# no database, so move the fresh one made by the roundcube installer
	mv /var/lib/dbconfig-common/sqlite3/roundcube/roundcube /data/roundcube.sqlite
    fi
    ln -s /data/roundcube.sqlite /var/lib/dbconfig-common/sqlite3/roundcube/roundcube
    chmod 777 /data
fi

# get hostname form SSL cert
HOSTNAME=`openssl x509 -in /data/certificate.pem -noout -subject | sed -e 's:.*CN=\(.*\)/.*:\1:'`
# and substitute it into the config files
find /etc/ -name '*.in' -print | while read file ; do
				     sed -e s/HOSTNAME/$HOSTNAME/ $file > ${file%.in}
				 done

<<<<<<< HEAD
#if [ ! -r /data/users.db ] ;then
#    sqlite3 -batch /data/users.db < /usr/lib/athen/schema.sql
#    chown www-data:www-data /data/users.db
#fi
=======
if [ ! -r /data/users.db ] ;then
    sqlite3 -batch /data/users.db < /usr/lib/athen/schema.sql
    chown www-data:www-data /data/users.db
fi
>>>>>>> 4cd1bd19cb47a08274b0afedb732e72e48e7cc24

exec /usr/bin/supervisord
