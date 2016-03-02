#!/bin/bash

USER=$1

umount /dev/mapper/$USER
cryptsetup close $USER
LOOP=`losetup | awk -v u=/data/home/$USER.img '$6==u {print $1}'`
losetup -d $LOOP
