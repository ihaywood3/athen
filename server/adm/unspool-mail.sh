#!/bin/bash
if [ -z "$1" ] ; then
    echo "Need username" >&2
    exit 1
fi

    cd `dirname $0`
    . ./utils.sh
    . ./cryptoloop.sh
    USER=$1
    HOME=/home/athen/home/$USER
    log "unspooling for $USER"
    OLDDIR=`pwd`
    cd /home/vmail/spool/$USER
    LOCKFILE=/var/lock/athen.$USER.lock
    (
	flock 9 || (
	    echo Couldnt get lock on $LOCKFILE >&2
	    log "unspool: Couldnt get lock on $LOCKFILE"
	    exit 1
	)
	for i in *.mail ; do
	    #openssl smime -decrypt -in $i -inform DER -recip $UHOME.pem -inkey $UHOME/private.key | \
	#	/usr/lib/dovecot/deliver -d $USER  && \
	    cat $i | $HOME/user-shim deliver --unspool || (
		STATUS=$?
		log "deliver.py failed with $STATUS"
	    )
	    rm -f $i
	done
    ) 9>$LOCKFILE
    rm -f $LOCKFILE
#fi
