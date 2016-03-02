#!/bin/bash
# create encrypted partition

USER=$1
GECOS=$2
read PASSWD
. ./utils.sh

if [ ! -e /data/home ] ; then
    mkdir -p /data/home
fi
cd /data/home
if ! grep -q $USER /etc/passwd ; then
    /usr/sbin/useradd -b /data/home -c "$GECOS" -g vmail -M -N $USER
    cp /etc/passwd /data/passwd.bak
fi
if [ ! -d /data/home/$USER ] ; then
    mkdir $USER
    chown $USER:vmail $USER
fi
if [ ! -e $USER.img ] ; then
    dd if=/dev/zero of=$USER.img bs=1M count=100
    chown $USER:vmail $USER.img
    losetup -f $USER.img
    LOOPDEV=`losetup | awk -v u=/data/home/$USER.img '$6==u {print $1}'`
    badblocks -s -w -t random -v $LOOPDEV
    printf "YES\n$PASSWD\n$PASSWD\n" | cryptsetup --force-password luksFormat $LOOPDEV -
    printf "$PASSWD\n" | cryptsetup open --type luks --key-file - $LOOPDEV $USER
    mkfs.ext4 -j /dev/mapper/$USER
    e2fsck -f /dev/mapper/$USER
    mount /dev/mapper/$USER $USER
    mkdir $USER/mail
    chown $USER:vmail $USER/mail
    openssl genpkey -out $USER/private.key -outform PEM -algorithm RSA
    chmod 600 $USER/private.key
    chown $USER:vmail $USER/private.key
    openssl pkey -in private.key -inform PEM -outform PEM -pubout -out $USER.pem
    # salted hash of password stored
    dd if=/dev/urandom of=$USER/salt bs=1 count=32
    password_checksum $PASSWD $USER
    echo -n $CHECKSUM > $USER/password 
    umount /dev/mapper/$USER
    losetup -d $LOOPDEV
    # report to hub
    # wget --certificate=/data/certificate.pem --private-key=/data/private.key --post-data="$USER,$GECOS" https://athen.net.au/newuser.sh
fi


