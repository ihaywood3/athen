#!/bin/bash

# assume mounted already
USER=$1
AVAIL=`df | awk -v u=/dev/mapper/$USER '$1==u {print $4}'`
if (( AVAIL > 50 )) ; then
    echo More than 50 meg, but resizing anyway
    # exit # exit if more than 50 meg available
fi
LOOPDEV=`losetup | awk -v u=/home/athen/home/$USER.img '$6==u {print $1}'`
umount /dev/mapper/$USER
dd if=/dev/urandom bs=1M count=50 >> /home/athen/home/$USER.img # add 50 meg
losetup -c $LOOPDEV
cryptsetup resize /dev/mapper/$USER
e2fsck -fp /dev/mapper/$USER
resize2fs /dev/mapper/$USER
mount /dev/mapper/$USER /home/athen/home/$USER
