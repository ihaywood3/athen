#!/bin/bash
set -e

DIR=`dirname $0`

USER=$1

. $DIR/utils.sh

scan_loop $USER
umount /dev/mapper/$USER
cryptsetup close $USER
losetup -d $LOOPDEV
