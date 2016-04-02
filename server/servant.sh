#!/bin/bash

# the servant is a bash script reunning constantly in the background, as root
# it reads commands from a FIFO and carries them out
# obviously a massive security hole, permissions on the FIFO must be carefully set

if [ ! -p /tmp/athenpipe ] ; then
    mkfifo /tmp/athenpipe
    #chown nobody:nobody /tmp/athenpipe
    chmod 600 /tmp/athenpipe
fi

while true; do
    IFS=':' read -a cmd < /tmp/athenpipe
    case "${cmd[0]}" in
	newuser)
	    echo "New user ${cmd[1]}"
	    ;;
	login)
	    echo "Login user ${cmd[1]}"
	    ;;
	quit)
	    rm /tmp/athenpipe
	    exit 0
	    ;;
    esac
done
