#!/bin/bash

# the main delivery script

# postfix should set $USER and a few other envs
# we should be running as the receipient user
# (presumably LDAP lookup has occurred to discover this?)
# see http://www.postfix.org/postconf.5.html#mailbox_command

cd `dirname $0`
. ./utils.sh

HOST=$(cat /etc/mailname)

if [ ! -d /home/athen/spool/$USER ] ; then
    mkdir -p /home/athen/spool/$USER
    chmod 700 /home/athen/spool/$USER
    #chown $USER /home/athen/spool/$USER
fi


log "delivery script for $USER"
log "id = `id`"
log "whoami = `whoami'"

if [ -e $HOME/private.key ] ; then
    # we are logged in, so deliver directly
    log "homedir is mounted, passing straight to Dovecot"
    exec /usr/lib/dovecot/deliver -d $USER
else
    if [ ! -r /home/athen/home/$USER.img ] ;then
	exit 67  # no such user. This shouldn't happen
    fi
    cd /home/athen/spool/$USER
    LOCKFILE=/var/lock/athen.$USER.lock
    (
	flock 9 || (
	    echo Couldnt get lock on $LOCKFILE >&2
	    log "spool: Couldnt get lock on $LOCKFILE"
	    exit 75 # temporary failure
	)
	FILE=`mktemp -p /home/athen/spool/$USER --suffix=.mail`
	log "saving email to temp FILE=$FILE"
	python ../python/filter.py $USER | openssl smime -encrypt -outform DER -stream -out $FILE /home/athen/home/$USER.pem
    ) 9>$LOCKFILE
    rm -f $LOCKFILE
fi
