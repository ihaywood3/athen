
# creates a background process which stays root and does the root-required work 
# creating user accounts
# and launches webserver as low-priviledge user

import os, pwd, multiprocessing, subprocess
#import cherrypy
import util

class RootController:
    """Controls the as-root process for creating user accounts"""
    
    def __init__(self,debug=False):
        if debug:
            path = ["sudo","/home/ian/athen/server/adm/server.sh"]
        else:
            path = ["/usr/local/athen/server/adm/server.sh"]
        self.pro = subprocess.Popen(path,stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)

    def run(self,cmd):
        cmd = "|".join(i.replace("\\","\\\\").replace("|","\\|") for i in cmd)
        self.pro.stdin.write(cmd+"\n")
        self.pro.stdin.flush()
        l = self.pro.stdout.readline()
        lc = l.strip().split(":")
        err = False
        errtxt = ""
        while lc[0] != "FINISH":
            if lc[0] == "PROGRESS":
                yield (int(lc[1]),lc[2])
            elif lc[0] == "ERROR":
                err = True
                errtxt += lc[1]
            else:
                errtxt += l # it might be some error output, so save it
            l = self.pro.stdout.readline()
            lc = l.strip().split(":")
        if err:
            raise util.AthenError(errtxt)

    def quit(self):
        self.pro.stdin.write("QUIT\n")
        self.pro.wait()
