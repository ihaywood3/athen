#!/bin/bash

while true; do
    sudo docker build -t ihaywood3/athen .
    sudo docker stop athen_devel
    sudo docker rm athen_devel
    sudo docker run -d -p 8443:443 -p 8025:25 -p 8080:80 -p 8993:993 -p 8587:587 --name="athen_devel" -h athen_devel -v /home/ian/data:/data ihaywood3/athen
    if ! sudo docker exec -t -i athen_devel /bin/bash ; then
	sudo docker stop athen_devel
	exit
    fi
done
