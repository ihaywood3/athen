#!/bin/bash

# assume mounted already
USER=$1
AVAIL=`df | awk -v u=/dev/mapper/$USER '$1==u {print $4}'`
if (( AVAIL > 50 )) ; then exit ; fi  # exit if more than 50 meg available
LOOP=`losetup | awk -v u=/data/home/$USER.img '$6==u {print $1}'`
umount /dev/mapper/$USER
dd if=/dev/urandom bs=1M count=50 >> /data/home/$USER.img # add 50 meg
losetup -c $LOOP
cryptsetup resize /dev/mapper/$USER
e2fsck -f /dev/mapper/$USER
resize2fs /dev/mapper/$USER
mount /dev/mapper/$USER /data/home/$USER
