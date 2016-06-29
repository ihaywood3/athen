#!/bin/bash

if [ ! -d /home/athen/spool/$USER ] ; then
    mkdir -p /home/athen/spool/$USER
    chmod 700 /home/athen/spool/$USER
    chown $USER /home/athen/spool/$USER
fi

if [ "`whoami`" == "root" ] ; then
    su $1 -c "$0 $1" && exit 0
fi

cd `dirname $0`
. ./utils.sh

USER=$1
HOST=$(cat /etc/mailname)
EMAIL=$USER@$HOST

if [ ! -r /home/athen/home/$USER ] ;then
    exit 67  # no such user
fi
if [ -e /home/athen/home/$USER/private.key ] ; then
    # we are logged in, so deliver directly
    /usr/lib/dovecot/deliver -d $USER
else

    cd /home/athen/spool/$USER
    LOCKFILE=/var/lock/athen.$USER.lock
    (
	flock 9 || (
	    echo Couldnt get lock on $LOCKFILE >&2
	    log "spool: Couldnt get lock on $LOCKFILE"
	    exit 75 # temporary failure
	)
	FILE=`mktemp -p /home/athen/spool/$USER --suffix=.mail`
	log "saving email FILE=$FILE"
	openssl smime -encrypt -outform DER -stream -out $FILE /home/athen/$USER.pem
    ) 9>$LOCKFILE
    rm -f $LOCKFILE
fi
