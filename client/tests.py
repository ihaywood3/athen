import os, os.path, sys, time, pudb, logging

import unittest
import tempfile

import base, imap

MESSAGE = "MacGuffin"
PIT_FILENAME="msg0001.pit"
PIT_TEXT="""001 Sender - Report                                          07 01/07/1996
002                                                                       
003 Report Run Number: 0001 Created:   27/08/2007     at    13:04:05
004 Surgery: xxxx Reports: 27/08/2007 13:04:05  to  07/07/2005 13:04:05      
009 ----------------------------------------------------------------------
010 Target GP                          xxxx      Target Provider No
019 ----------------------------------------------------------------------
020 Your Ref.   Patient Name                   Lab Ref.        Test
021             Bloggs, John
029 ----------------------------------------------------------------------
100 Start Patient :       Bloggs,John
101                       
104                       Birthdate: 28/5/1956
105                       Telephone: 12345678
109                                                                       
110 Your Reference :     12345 
112 Medicare Number:      31023758309
123 Addressee :           test.org.eight@localhost                    246564QX
129                                                                       
200 Start of Result:
204 Collected :           24/08/2005
205 Name of Test :        Sender - Report
206 Reported :            26/08/2005
301  This is some example text in the field   (MacGuffin)
301 
319                                                                       
390 End of Report :
399 ----------------------------------------------------------------------
999 END OF LISTING - Run Number:0001  07/07/2005  13:04:05
"""

sys.path.append("../lib")
import util

class MainTestCase(unittest.TestCase):
    
    def setUp(self):
        logging.basicConfig(level=logging.DEBUG,format="%(asctime)s %(filename)s:%(lineno)d  %(msg)s")
        self.db1_fd, self.db1_name = tempfile.mkstemp()
        self.db2_fd, self.db2_name = tempfile.mkstemp()
        self.basedir = os.path.expanduser("~/athen_test/")
        os.system("rm -R {}".format(self.basedir))
        os.mkdir(self.basedir)
        for i in ["1","2"]:
            clientdir = os.path.join(self.basedir,"client%s/" % i)
            os.mkdir(clientdir)
            os.mkdir(clientdir+"downloads/")
            os.mkdir(clientdir+"errors/")
            os.mkdir(clientdir+"uploads/")
            os.mkdir(clientdir+"waiting/")

    def runTest(self):
        pass
    
    def test_messages(self):
        emailer1 = imap.Emailer(dict(
            dbfile=self.db1_name,
            debug=True,
            username='test.org.seven',
            download_path=os.path.join(self.basedir,"client1","downloads"),
            password='foobar123',
            host='localhost',
            timeout=5,
            upload_path=os.path.join(self.basedir,"client1","uploads"),
            errors_path=os.path.join(self.basedir,"client1","errors"),
            waiting_path=os.path.join(self.basedir,"client1","waiting")))
        emailer2 = imap.Emailer(dict(
            dbfile=self.db2_name,
            debug=True,
            username='test.org.eight',
            download_path=os.path.join(self.basedir,"client2","downloads"),
            password='foobar123',
            host='localhost',
            timeout=5,
            upload_path=os.path.join(self.basedir,"client2","uploads"),
            errors_path=os.path.join(self.basedir,"client2","errors"),
            waiting_path=os.path.join(self.basedir,"client2","waiting")))
        #emailer1.loop_thread()
        #emailer2.loop_thread()
        logging.debug("MAINTHREAD writing PIT text")
        with open(os.path.join(self.basedir,"client1","uploads",PIT_FILENAME),"w") as f:
            f.write(PIT_TEXT)
        emailer1.scan_directories()
        emailer2.get_messages()
        d = os.path.join(self.basedir,"client2","downloads")
        found_a_file = False
        for i in os.listdir(d):
            logging.debug("MAINTHREAD found file %s" % i)
            f = os.path.join(d,i) 
            with open(f,"r") as fd:
                contents = fd.read()
            if MESSAGE in contents:
                found_a_file = True
                os.unlink(f) # pretend we are an EMR and delete the received file
        assert found_a_file
        emailer2.check_consumed_files()
        emailer1.get_messages()
        emailer1.logout_imap()
        emailer2.logout_imap()
        db1 = base.DB(self.db1_name)
        n = db1.get_sent_files_status()
        #emailer1.set_external_quit()
        #emailer2.set_external_quit()
        #emailer2.thread.join()
        assert n[PIT_FILENAME][0] == imap.STATUS_DELIVERED

    def test_web_receive(self):
        emailer1 = imap.Emailer(dict(
            dbfile=self.db1_name,
            debug=True,
            username='test.org.seven',
            download_path=os.path.join(self.basedir,"client1","downloads"),
            password='foobar123',
            host='localhost',
            timeout=5,
            upload_path=os.path.join(self.basedir,"client1","uploads"),
            errors_path=os.path.join(self.basedir,"client1","errors"),
            waiting_path=os.path.join(self.basedir,"client1","waiting")))        
        logging.debug("MAINTHREAD writing PIT text")
        with open(os.path.join(self.basedir,"client1","uploads",PIT_FILENAME),"w") as f:
            f.write(PIT_TEXT)
        emailer1.scan_directories()           
        input("Log on to test.org.eight and reply")
        emailer1.get_messages() # get the return receipt
        emailer1.logout_imap()
        db1 = base.DB(self.db1_name)
        n = db1.get_sent_files_status()
        assert n[PIT_FILENAME][0] == imap.STATUS_DELIVERED  

    def test_web_sent(self):
        emailer1 = imap.Emailer(dict(
            dbfile=self.db1_name,
            debug=True,
            username='test.org.seven',
            download_path=os.path.join(self.basedir,"client1","downloads"),
            password='foobar123',
            host='localhost',
            timeout=5,
            upload_path=os.path.join(self.basedir,"client1","uploads"),
            errors_path=os.path.join(self.basedir,"client1","errors"),
            waiting_path=os.path.join(self.basedir,"client1","waiting")))    
        input("Log on to test.org.eight and send message to test.org.seven")
        emailer1.get_messages()
        d = os.path.join(self.basedir,"client1","downloads")
        found_a_file = False
        for i in os.listdir(d):
            logging.debug("MAINTHREAD found file %s" % i)
            pudb.set_trace()
            f = os.path.join(d,i) 
            with open(f,"r") as fd:
                contents = fd.read()
            if MESSAGE in contents:
                found_a_file = True
                os.unlink(f) # pretend we are an EMR and delete the received file
        assert found_a_file    
        emailer1.check_consumed_files()
        emailer1.logout_imap()
        print("You should have read receipt")

    def tearDown(self):
        os.close(self.db1_fd)
        os.unlink(self.db1_name)
        os.close(self.db2_fd)
        os.unlink(self.db2_name)
        os.system("rm -R %s" % self.basedir)
        

def go():
    m = MainTestCase()
    m.setUp()
    m.test_web_sent()
    m.tearDown()

go()


