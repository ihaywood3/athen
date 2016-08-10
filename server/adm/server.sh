#!/bin/bash

# this bash "server" is a bash script running constantly in the background, as root
cd `dirname $0`

while true; do
    IFS='|' read -a cmd
    case "${cmd[0]}" in
	NEWUSER)
	    TUID=${cmd[1]}
	    O=${cmd[2]}
	    PASSWD=${cmd[3]} ./make-home.sh "${TUID}" "${O}" || echo "ERROR:script failed"
	    echo "FINISH:"
	    ;;
	LOGIN)
	    echo "Login user ${cmd[1]}"
	    ;;
	QUIT)
	    echo "server.sh has quit"
	    exit 0
	    ;;
    esac
    unset cmd
done
