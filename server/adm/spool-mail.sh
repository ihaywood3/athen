#!/bin/bash

SPOOLMAX=51200 # 50 meg

# the main delivery script
# we should be running as user vmail
# username set on $1
cd `dirname $0`
. ./utils.sh

HOST=$(cat /etc/mailname)
USER=$1
EMAIL=$USER@$HOST
UHOME=/home/athen/home/$USER
export HOME=/home/vmail

log "delivery script for $USER"
log "id = `id`"
log "whoami = `whoami`"

if [ -e $UHOME/mail ] ; then
    # we are logged in, so deliver
    log "homedir is mounted, passing straight to Python filter and then Dovecot deliver"
    # use the shim to become the target user
    exec $UHOME/user-shim deliver $USER --direct
else
    if [ ! -r /home/athen/home/$USER.img ] ; then
	exit 67  # no such user. This shouldn't happen
    fi
    cd /home/vmail/spool/$USER
    LOCKFILE=/var/lock/athen.$USER.lock
    (
	flock -w 10 9 || (
	    echo Couldnt get lock on $LOCKFILE >&2
	    log "spool: Couldnt get lock on $LOCKFILE"
	    exit 75 # temporary failure
	)
	spool_size $USER
	if (( SPOOLSIZE > SPOOLMAX )) ; then # user has more than SPOOLMAX
	    echo Spool bigger than $SPOOLMAX k, rejecting mail
	    log " Spool bigger than $SPOOLMAX k, rejecting mail"
	    exit 75 # temporary failure
	fi
	FILE=$(mktemp -p /home/vmail/spool/$USER --suffix=.tmpmail)
	log "saving email to temp FILE=$FILE"
	# encrypt (using vmail's keying) to target user
	gpg -r "$EMAIL" --no-tty --batch --yes --trust-model tofu --encrypt > $FILE
	# save and then rename to guard against reader catching half-written file
	mv $FILE $(basename $FILE .tmpmail).mail 
    ) 9>$LOCKFILE
    rm -f $LOCKFILE
fi
