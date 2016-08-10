#!/bin/bash

function log()
{
   printf "%s  %s\\n" "`date +%F\ %H:%M:%S,%N`" "$1" >> /var/log/athen/scripts.log
}

exec 2>&1 >> /var/log/athen/scripts.log

