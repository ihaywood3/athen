#!/bin/bash

# this bash "server" is a bash script running constantly in the background, as root
# it reads commands from a FIFO and carries them out
# obviously the mother of all security holes, permissions on the FIFO must be carefully set

. ./utils.sh
. ./cryptoloop.sh

if [ ! -p /tmp/athen.control.fifo ] ; then
    mkfifo /tmp/athenpipe
    #chown nobody:nobody /tmp/athen.control.fifo
    chown ian:users /tmp/athen/control.fifo
    chmod 600 /tmp/athen.control.fifo
fi

while true; do
    IFS='|' read -a cmd < /tmp/athen.control.fifo
    case "${cmd[0]}" in
	NEWUSER)
	    UID=${cmd[1]}
	    O=${cmd[2]}
	    PASSWD=${cmd[3]}
	    PASSWD=${PASSWD//P0/|}  # undo a basic escaping for password
	    PASSWD=${PASSWD//P1/P}
	    log "NEWUSER uid=${UID} o=${O}"
	    make_home "${UID}" "${O}" "${PASSWD}"
	    ;;
	login)
	    log "Login user ${cmd[1]}"
	    ;;
	QUIT)
	    log "servant has quit"
	    rm /tmp/athen.control.fifo
	    exit 0
	    ;;
    esac
done
