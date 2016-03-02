#!/bin/bash

. /usr/share/athen/adm/utils.sh

<<<<<<< HEAD
if [ ! -r /data/home/$USER.pem ] ;then
    exit 67  # no user
fi
USERTYPE=`getent passwd $USER | cut -d ':' -f 5 | cut -d ',' -f 5`
if [ "$USERTYPE" == "X" ] ; then
    exit 77 # permission denied
fi
=======
USER=$1
if [ ! -r /data/home/$USER.pem ] ;then
    exit 67  # no user
fi

>>>>>>> 4cd1bd19cb47a08274b0afedb732e72e48e7cc24
if [ ! -d /data/spool/$USER ] ; then
    mkdir /data/spool/$USER
    chmod 700 /data/spool/$USER
fi
cd /data/spool/$USER
(
    flock -n 9 || (
	echo Couldnt get lock
	exit 75 # temporary failure
    )
    FILE=`mktemp -p /data/spool/$USER --suffix=.mail`
    openssl pkeyutl -encrypt -pubin -keyform PEM -inkey /data/home/$USER.pem -out $FILE
) 9>/var/lock/athen.$USER.lock
