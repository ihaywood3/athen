#!/bin/bash

function log()
{
   printf "%s  %s\\n" "`date +%F\ %H:%M:%S,%N`" "$1" >> /var/log/athen/scripts.log
}

#exec 2>&1 >> /var/log/athen/scripts.log

# find size of user's spool, in k,
function spool_size ()
{
    SPOOLSIZE=`du -s -B 1024 /home/vmail/spool/$1 | awk '{print $1}'`
}
