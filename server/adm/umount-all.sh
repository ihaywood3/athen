#!/bin/bash
set -e

DIR=`dirname $0`
. $DIR/utils.sh
. $DIR/cryptoloop.sh

log "umount-all.sh"

OLDPWD=$(pwd)

TMPDIR=/tmp/athen.umount.$$
mkdir $TMPDIR
chmod 700 $TMPDIR
cd $TMPDIR

mount > mounts
ps axu --no-headers > ps

awk '
  FILENAME == "ps" &&  $11 == "dovecot/imap" {online["/dev/mapper/" $1]=1 } 
  FILENAME == "mounts" && !($1 in online) && substr($3,0,11) == "/home/athen" {print substr($1,13)}
' ps mounts | while read ; do 
    umount_home "$REPLY" 
done

cd $OLDPWD
rm -R $TMPDIR

