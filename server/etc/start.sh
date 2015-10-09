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

# get hostname form SSL cert
HOSTNAME=`openssl x509 -in /data/certificate.pem -noout -subject | sed -e 's:.*CN=\(.*\)/.*:\1:'`
# and substitute it into the config files
find /etc/ -name '*.in' -print | while read file ; do
				     sed -e s/HOSTNAME/$HOSTNAME/ $file > ${file%.in}
				 done
exec /usr/bin/supervisord
