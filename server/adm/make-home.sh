#!/bin/bash

function cleanup()
{
    if [ "$ENCRYPT_FLAG" == "Y" ] ; then
	cd /
	if [ -n "$LOOPDEV" ] ; then
	    umount /dev/mapper/$USER || true
	    cryptsetup close $USER || true
	    losetup -d $LOOPDEV || true
	fi
    fi
}

trap "cleanup" 0

cd `dirname $0`
SCRIPTDIR=`pwd`

set -e
. ./cryptoloop.sh
GPGSCRIPT=`pwd`/gpg.sh

# create new user
# environemnt set as follows:
# USER=new UNIX username
# UID=new numberic user ID
# FULLNAME=the human username (aka LDAP "cn" or "o" value)
# PASSWD= the new password
# ENCRYPT_FLAG= Y if we want encryption

if [ ! -e /home/athen/home ] ; then
    mkdir -p /home/athen/home
    chown athen:vmail /home/athen/home
fi
if [ ! -e /home/vmail/spool ] ; then
    mkdir -p /home/vmail/spool
    chown vmail:vmail /home/vmail/spool
fi
if grep -q $USER: /etc/passwd ; then
    echo "ERROR:user already exists in /etc/passwd"
    exit 0
fi
if [ -e $USER.img ] ; then
    echo "ERROR:image file already exists /home/athen/home/$USER.img"
    exit 0
fi

cd /home/athen/home
echo "PROGRESS:1:creating user directory"
mkdir $USER
chown $NUID:2000 $USER
chmod 755 $USER

if [ "$ENCRYPT_FLAG" == "Y" ] ; then
    echo "PROGRESS:2:creating drive image"
    dd status=none if=/dev/zero of=$USER.img bs=4M count=25
    chown $NUID:2000 $USER.img
    echo "PROGRESS:8:set up loopback device"
    losetup -f $USER.img
    scan_loop $USER
    if [ "z$LOOPDEV" == "z" ] ; then
	echo "ERROR:cannot find LOOPDEV"
	exit 0
    fi
    echo "PROGRESS:9:randomising drive data"
    badblocks -w -t random -v $LOOPDEV 2> /dev/null
    echo "PROGRESS:12:encrypting drive"
    printf "$PASSWD" | cryptsetup --force-password luksFormat --key-file=- $LOOPDEV
    echo "PROGRESS:50:opening encrypted drive"
    printf "$PASSWD" | cryptsetup open --type luks --key-file=- $LOOPDEV $USER
    echo "PROGRESS:65:creating filesystem"
    mkfs.ext4 -qj /dev/mapper/$USER 
    echo "PROGRESS:67:checking filesystem"
    e2fsck -fp /dev/mapper/$USER > /dev/null
    mount /dev/mapper/$USER $USER
    cd $USER
    chown $NUID:2000 .
    chown $NUID:2000 *
    chmod u+rwx .
else
    cd $USER
fi
unset PASSWD


# set up the shim for this user
cp /usr/local/lib/athen/user-shim $USER
chown $NUID:2000 $USER/user-shim
chmod 4755 $USER/user-shim

# make private key via gpg
echo "PROGRESS:70:generating private key"
#openssl req -new -x509 -nodes -outform PEM -out $USER.pem -newkey rsa -keyout $USER/private.key -subj "/DC=email/DC=athen/O=$REALNAME" -days 3600 -batch > /dev/null
HOME=/home/athen/home/$USER chpst -u :$NUID:2000 $GPGSCRIPT user_gen_key | chpst -u vmail:vmail $GPGSCRIPT vmail_accept_key
HOME=/home/athen/home/$USER chpst -u :$NUID:2000 $GPGSCRIPT kill_agent

echo "PROGRESS:80:creating files"
#chmod 600 $USER/private.key
#chown $NUID:200 $USER/private.key
mkdir -m 700 mail
chown $NUID:2000 mail
mkdir -m 730 /home/vmail/spool/$USER # 730=group vmail can write,execute but not read
chown $NUID:2000 /home/vmail/spool/$USER

#/usr/bin/sqlite3 $USER/user.db < $SCRIPTDIR/user.db.sql
#chown $NUID:2000 user.db
#chmod 700 $USER/user.db

echo "PROGRESS:82:unmounting"
cd ..
sync
sleep 1 # give time for the above file operations to be committed to disc
