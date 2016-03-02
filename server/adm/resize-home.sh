#!/bin/bash

# assume mounted already
USER=$1
AVAIL=`df | awk -v u=/dev/mapper/$USER '$1==u {print $4}'`
TOTAL=`df | awk -v u=/dev/mapper/$USER '$1==u {print $2}'`
USERTYPE=`getent passwd $USER | cut -d ':' -f 5 | cut -d ',' -f 5`
QUOTA=250000  # 250 meg
if [ "$USERTYPE" == "P" ] ; then
    # provisional user
    QUOTA=100000  # 100 meg
fi
if ["$USERTYPE" == "X" ] ;then
    # restrcited user: shouldn't really get here
    exit 77
fi
if (( AVAIL > 50000 )) ; then exit ; fi  # exit if more than 50 meg available
if (( TOTAL+50000 > QUOTA \\ ; then exit ; fi # exit if would exceed quota
LOOP=`losetup | awk -v u=/data/home/$USER.img '$6==u {print $1}'`
umount /dev/mapper/$USER
dd if=/dev/urandom bs=1M count=50 >> /data/home/$USER.img # add 50 meg
losetup -c $LOOP
cryptsetup resize /dev/mapper/$USER
e2fsck -f /dev/mapper/$USER
resize2fs /dev/mapper/$USER
mount /dev/mapper/$USER /data/home/$USER
