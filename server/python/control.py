#!/bin/bash
# creates a background process which stays root and does the root-required work 
# creating user accounts
# note server.py is responsible for lauching things and dropping root privileges

import os, pwd, multiprocessing, subprocess, select, logging

import util

class RootController:
    """Controls the as-root process for creating user accounts"""
    
    def __init__(self,debug=False):
        if debug:
            path = ["sudo","/home/ian/athen/server/adm/server.sh"]
        else:
            path = ["/usr/local/lib/athen/adm/server.sh"]
        self.pro = subprocess.Popen(path,stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)

    def run(self,cmd):
        cmd = b"|".join(bytes(str(i),"utf-8").replace(b"\\",b"\\\\").replace(b"|",b"\\|") for i in cmd)
        self.pro.stdin.write(cmd+b"\n")
        self.pro.stdin.flush()
        l = self.pro.stdout.readline()
        logging.debug(repr(l))
        lc = l.strip().split(b":")
        err = False
        errtxt = ""
        while lc[0] != b"FINISH":
            if lc[0] == b"PROGRESS":
                yield (int(lc[1]),str(lc[2],"utf-8"))
            elif lc[0] == b"ERROR":
                err = True
                errtxt += str(lc[1],"utf-8")
                logging.debug("errtxt %s",repr(lc[1]))
            else:
                errtxt += str(l,"utf-8") # it might be some error output, so save it
            l = self.pro.stdout.readline()
            logging.debug(repr(l))
            lc = l.strip().split(b":")
        if err:
            raise util.AthenError(errtxt)

    def quit(self):
        self.pro.stdin.write(b"QUIT\n")
        self.pro.stdin.flush()
        self.pro.stdin.close()
        self.pro.stdout.close()
        self.pro.wait(timeout=10)
