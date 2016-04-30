#!/bin/bash

. ./utils.sh

# expects $USER as $1 and PASSWD on stdin
USER=$1

if [ ! -e /home/athen/home/$USER/secring.gpg ] ; then
    losetup -f /home/athen/home/$USER.img
    log "trying to mount USER=$USER"
    scan_loop $USER
    log "LOOPDEV=$LOOPDEV"
    read PASSWD
    if printf "$PASSWD" | cryptsetup open --type luks --key-file=- $LOOPDEV $USER ; then
       log "crypto enabled: about to mount"
       mount /dev/mapper/$USER /home/athen/home/$USER
       log "Directory mounted"
    else
	log "no cryptoloop established: usually wrong password"
	losetup -d $LOOPDEV
	exit 1
    fi
else
    read PASSWD
    password_checksum $PASSWD $USER
    CHECKSUM2=`cat /home/athen/home/$USER/password`
    if [ "$CHECKSUM" == "$CHECKSUM2" ] ; then
	log "Password check passed"
	exit 0
    else
	echo"Password check failed"
	exit 1
    fi
fi

