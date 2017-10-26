#!/usr/bin/python3

import sys, threading, os, readline, re

uname = sys.argv[1]

input_path = "/var/run/athen/{}.input".format(uname)
output_path = "/var/run/athen/{}.output".format(uname)

if not os.access(input_path,os.R_OK):
    os.umask(0)
    os.mkfifo(input_path)
    os.mkfifo(output_path)
    
def to_display():
    while True:
        with open(input_path,"rb") as ipipe:
            data = ipipe.read()
        # remove ridiculous end of line padding
        lines = data.split(b"\r\n")
        data = b"\n".join(re.sub(b" +$",b" ",i) for i in lines)
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()


t = threading.Thread(target=to_display,daemon=True)
t.start()

while True:
    cmd = input("")
    cmd = bytes(cmd,"ascii")
    with open(output_path,"wb") as opipe:
        opipe.write(cmd+b"\r\n")
    if cmd == b"quit": break

