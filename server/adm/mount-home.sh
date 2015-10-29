#!/bin/bash

. /usr/share/athen/adm/utils.sh

# expects $USER and $PASSWD already set

LOOPDEV=`losetup | awk -v u=/data/home/$USER.img '$6==u {print $1}'`
if [ "$LOOPDEV" == ""] ; then
    losetup -f /data/home/$USER.img
    LOOPDEV=`losetup | awk -v u=/data/home/$USER.img '$6==u {print $1}'`
    cryptsetup open --type luks --key-file - $LOOPDEV $USER
    mount /dev/mapper/$USER /data/home/$USER
else
    password_checksum $PASSWD $USER
    CHECKSUM2=`cat /data/home/$USER/password`
    if [ "$CHECKSUM" == "$CHECKSUM2" ] ; then
	exit 0
    else
	echo Password check failed
	exit 1
    fi
fi

# decrypt spooled mail
if [ -d /data/spool/$USER ] ; then
    (
	flock -n 9 || exit 1
	cd /data/spool/$USER
	HOME=/data/home/$USER
	for i in `ls *.mail` ; do
	    openssl pkeyutl -decrypt -in $i -inkey /data/home/$USER/private.key -keyform PEM | su -m -c "deliver" $USER
	    rm $i
	    /usr/share/athen/adm/resize-home.sh $USER
	done
    ) 9>/var/lock/athen.$USER.lock
fi
