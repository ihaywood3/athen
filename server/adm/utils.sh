#!/bin/bash

set -e

date >> /var/log/athen/scripts.log
echo Script $0 >> /var/log/athen/scripts.log

exec >> /var/log/athen/scripts.log 2>&1


function log ()
{
    echo $1 >> /var/log/athen/scripts.log
}
