#!/bin/bash

# this bash "server" is a bash script running constantly in the background, as root
cd `dirname $0`

while true; do
    IFS='|' read -a cmd
    case "${cmd[0]}" in
	NEWUSER)
	    USER=${cmd[1]} NUID=${cmd[2]} FULLNAME=${cmd[3]} PASSWD=${cmd[4]} ENCRYPT_FLAG=${cmd[5]} MAILNAME=${cmd[6]} ./make-home.sh || echo "ERROR:script failed"
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
