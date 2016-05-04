'''

The Windows main script
adapted from example by Alex Baker (7/7/2008) http://essiene.blogspot.com/2005/04/python-windows-services.html

 Usage : python aservice.py install
 Usage : python aservice.py start
 Usage : python aservice.py stop
 Usage : python aservice.py remove
 
 C:\>python aservice.py  --username <username> --password <PASSWORD> --startup auto install

'''


import win32service
import win32serviceutil
import win32api
import win32con
import win32event
import win32evtlogutil
import os, logging, loggin.handlers

import base, imap


class Emailer(imap.Emailer):
    
    def wait(self,timeout):
        win32event.WaitForSingleObject(self.hWaitStop, int(timeout*1000))

class aservice(win32serviceutil.ServiceFramework):
   
    _svc_name_ = "athen"
    _svc_display_name_ = "ATHEN downloader"
    _svc_description_ = "Downloads/uploads messages via email on the ATHEN system"
         
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)           

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.imap.running = False
        win32event.SetEvent(self.hWaitStop)                    
         
    def SvcDoRun(self):
        import servicemanager
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,servicemanager.PYS_SERVICE_STARTED,(self._svc_name_, ''))
        nthandler = logging.handlers.NTEventLogHandler("ATHEN service")
        logger = logging.getLogger()
        logger.addHandler(nthandler)
        logging.getLogger().setLevel(logging.INFO)
        try:
            self.db = base.DB()
            logger.addHandler(base.SQLiteHandler(self.db))
            self.imap = Emailer(db)
            self.imap.hWaitStop = self.hWaitStop
            self.imap.loop()
        except:
            logging.exception("in iniitialisation")
        servicemanager.LogInfoMsg("ATHEN service - STOPPED")
   
               
      
def ctrlHandler(ctrlType):
    return True
                  
if __name__ == '__main__':   
    win32api.SetConsoleCtrlHandler(ctrlHandler, True)   
    win32serviceutil.HandleCommandLine(aservice)