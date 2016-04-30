#!/bin/bash

set -e

date >> /var/log/athen.log
echo Script $0 >> /var/log/athen.log

exec >> /var/log/athen.log 2>&1

function scan_loop()
{
   LOOPDEV=`losetup -a | awk -F '[:() ]+' -v u=/home/athen/home/$1.img '$4==u {print $1; nextfile}'`
}

function password_checksum ()
{
    CHECKSUM=`echo -n $1 | cat /home/athen/home/$2/salt -`
    COUNTER=0
    while [  $COUNTER -lt 1000 ]; do
        CHECKSUM=`echo -n $CHECKSUM | sha512sum | awk '{print $1}'`
        let COUNTER=COUNTER+1 
    done
    return 0
}

function log ()
{
    echo $1 >> /var/log/athen.log
}
