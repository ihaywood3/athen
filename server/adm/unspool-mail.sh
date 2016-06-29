#!/bin/bash

if [ "`whoami`" == "root" ] ; then
    su $1 -c "$0 $1"
else
    cd `dirname $0`
    . ./utils.sh
    USER=$1
    UHOME=/home/athen/home/$USER
    cd /home/athen/spool/$USER
    LOCKFILE=/var/lock/athen.$USER.lock
    (
	flock 9 || (
	    echo Couldnt get lock on $LOCKFILE >&2
	    log "unspool: Couldnt get lock on $LOCKFILE"
	    exit 1
	)
	for i in *.mail ; do
	    openssl smime -decrypt -in $i -inform DER -recip $UHOME.pem -inkey $UHOME/private.key | \
		/usr/lib/dovecot/deliver -d $USER  && \
		rm -f $i
	done
    ) 9>$LOCKFILE
    rm -f $LOCKFILE
fi
