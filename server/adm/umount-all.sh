#!/bin/bash
set -e

DEBUG=0

if [ $1 == "-d" ] ; then
    set -x
    DEBUG=1
fi

DIR=`dirname $0`
. $DIR/utils.sh
. $DIR/cryptoloop.sh

OLDPWD=$(pwd)

TMPDIR=/tmp/athen.umount.$$
mkdir $TMPDIR
chmod 700 $TMPDIR
cd $TMPDIR

mount > mounts
ps axu --no-headers > ps

if [ ! -z $DEBUG ] ; then
    echo Mounts::
    cat mounts
    echo Ps::
    cat ps
fi

awk '
  FILENAME == "ps" &&  $11 == "dovecot/imap" {online["/dev/mapper/" $1]=1 } 
  FILENAME == "mounts" && !($1 in online) && substr($3,0,11) == "/home/athen" {print substr($1,13)}
' ps mounts | while read ; do 
    umount_home "$REPLY" 
done

cd $OLDPWD
rm -R $TMPDIR

