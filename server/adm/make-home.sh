#!/bin/bash
set -e
# create encrypted partition

cd `dirname $0`

USER=$1
REALNAME=$2
read PASSWD
. ./utils.sh
. ./gpg.sh

if [ ! -e /home/athen/home ] ; then
    mkdir -p /home/athen/home
fi
cd /home/athen/home
if ! grep -q $USER /etc/passwd ; then
    /usr/sbin/useradd -b /home/athen/home -c "$REALNAME,,," -g vmail -M -N $USER
fi

if [ ! -e $USER.img ] ; then
    dd if=/dev/zero of=$USER.img bs=1M count=100
    chown $USER:vmail $USER.img
fi
if [ ! -e $USER/private.key ] ; then
    losetup -f $USER.img
    scan_loop $USER
    badblocks -s -w -t random -v $LOOPDEV
    printf "$PASSWD" | cryptsetup --force-password luksFormat --key-file=- $LOOPDEV
    printf "$PASSWD" | cryptsetup open --type luks --key-file=- $LOOPDEV $USER
    mkfs.ext4 -j /dev/mapper/$USER
    e2fsck -fp /dev/mapper/$USER
    mkdir $USER
    chown $USER:vmail $USER
    chmod 755 $USER
    mount /dev/mapper/$USER $USER
    mkdir $USER/mail
    chown $USER:vmail $USER/mail
    #openssl genpkey -out $USER/private.key -outform PEM -algorithm RSA
    #chmod 600 $USER/private.key
    #chown $USER:vmail $USER/private.key
    #openssl pkey -in $USER/private.key -inform PEM -outform PEM -pubout -out $USER.pem
    # salted hash of password stored
    # make GnuPG key
    gen_key $USER "$REALNAME"
    # make salted password
    dd if=/dev/urandom of=$USER/salt bs=1 count=32
    chown $USER:vmail $USER/salt
    chown 600 $USER/salt
    password_checksum $PASSWD $USER
    echo -n $CHECKSUM > $USER/password
    chmod 600 $USER/password
    chown $USER:vmail $USER/password
    sleep 1
    umount /dev/mapper/$USER
    cryptsetup close $USER
    losetup -d $LOOPDEV
fi


