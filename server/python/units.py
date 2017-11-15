#!/usr/bin/env python3
import os, os.path, sys, time, pdb, unittest, subprocess, sys, re, pwd, email
try:
    import pudb as pdb
except:
    import pdb
from unittest import skip
import logging
sys.path.append("../../lib")

import myldap, config, control, server, deliver, accounting, mailfilter, userdb
import pit, hl7.letter

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class theTestCase(unittest.TestCase):

    def setUp(self):
        self.rc = control.RootController(debug=True)
        server.root_controller = self.rc
        server.application.config['TESTING'] = True
        server.application.secret_key = "testing key"
        self.app = server.app.test_client()
        time.sleep(1) # give server.sh time to initialise.
        

    def tearDown(self):
        self.delete_all_ldap()
        self.rc.quit()
        os.system("sudo /usr/local/lib/athen/adm/umount-all.sh")
        os.system("sudo rmdir /home/athen/home/test*/ 2> /dev/null")
        os.system("sudo rm -f /home/athen/home/test*.img")
        os.system("sudo rm -Rf /home/vmail/spool/test*")
        os.system("sudo rm -f %s/test*.ps" % config.latex_path)
        #os.system("sudo userdel test.organisation")

            
    def delete_all_ldap(self):
        with myldap.LDAP(dn=config.ldap_user,password=config.password) as l:
            for i in l.query(query="(objectClass=athenPerson)",fields=["cn"]):
                i.delete()
            for i in l.query(query="(objectClass=athenOrganisation)",fields=["o"]):
                i.delete()
            
    def make_org(self,testing="yes",o="Test Organisation",encrypt=False):
        if encrypt:
            encrypt_flag = 'yes'
        else:
            encrypt_flag = 'no'
        rv = self.app.post("/config/acct/save",data=dict(
            type="O",
            userPassword="foobar123",
            userPassword_repeat="foobar123",
            o=o,
            l="Werribee",
            postalCode="3030",
            businessCategory="general practice",
            street="1 Foo St",
            st="Victoria",
            telephoneNumber="97421111",
            _testing=testing,
            encryptFlag=encrypt_flag,
        ),follow_redirects=True)
        print(repr(rv.data))
        assert "setProgress(100,\"Completed\");" in str(rv.data)
        return rv

    def test_newuser_forreal(self):
        # WARNING: will be very slow
        self.make_org("no")
        time.sleep(10)
        assert os.path.exists("/home/athen/home/test.organisation")
        assert os.path.exists("/home/athen/home/test.organisation.img")

    def login(self, username, password):
        return self.app.post('/config/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/config/logout', follow_redirects=True)

    def test_make_org_quick(self):
        rv = self.make_org()
        l = myldap.LDAP(dn=config.ldap_user,password=config.password,default_base=config.public_base_dn)
        res = l.query("(&(o=Test Organisation)(objectclass=athenOrganisation))")
        assert res[0]['telephoneNumber'] == "97421111"

    def test_users(self):
        self.make_org()
        rv = self.login("test.organisation","foobar123")
        assert b"Logged in" in rv.data
        # make a user
        rv = self.app.post("/config/user/save",data=dict(
            givenName="Ian",
            sn="Haywood",
            medicalSpecialty="psychiatrist",
            providerNumber="246564AK"),follow_redirects=True)
        assert b"New person saved successfully" in rv.data
        # test that we can't create same user again
        rv = self.app.post("/config/user/save",data=dict(
            givenName="Ian",
            sn="Haywood",
            medicalSpecialty="psychiatrist",
            providerNumber="246564AK"),follow_redirects=True)
        logging.debug(repr(rv.data))
        assert b"user of same name exists" in rv.data
        # test we can change a user
        rv = self.app.post("/config/user/update",data=dict(medicalSpecialty='child psychiatrist',
            givenName="Ian",
            sn="Haywood"),follow_redirects=True)
        assert b"Person updated successfully" in rv.data
        # check LDAP to confirm
        l = myldap.LDAP(dn=config.ldap_user,password=config.password,default_base=config.public_base_dn)
        res = l.query(query="(sn=Haywood)")
        assert res[0]['medicalSpecialty'] == "child psychiatrist"
        # try to use some invalid data
        rv = self.app.post("/config/user/save",data=dict(
            givenName="John",
            sn="Heywood",
            medicalSpecialty="psychiatrist",
            providerNumber="246"),follow_redirects=True)
        assert b"Medicare provider number with value of" in rv.data

    def test_modify_org(self):
        self.make_org()
        rv = self.login("test.organisation","foobar123")
        assert b"Logged in" in rv.data
        # modify a user
        rv = self.app.post("/config/acct/update",data=dict(
            type="O",
            status_closed="yes",
            telephoneNumber="97421112"),follow_redirects=True)
        logging.debug(repr(rv.data))
        assert b"Record modified" in rv.data
        l = myldap.LDAP(dn=config.ldap_user,password=config.password,default_base=config.public_base_dn)
        res = l.query(query="(&(o=Test Organisation)(objectclass=athenOrganisation))")
        assert res[0]['telephoneNumber'] == "97421112"
        assert res[0]['status'] == "X"

    def test_confirm_org(self):
        self.make_org()
        l = myldap.LDAP(dn=config.ldap_user,password=config.password,default_base=config.public_base_dn)
        # fake nonce
        rv = self.app.post("/config/confirm",data=dict(
            nonce='A123456789',
            uid="test.organisation"),follow_redirects=True)
        logging.debug(repr(rv.data))
        assert b"Key is not valid" in rv.data
        res = l.query(query="(&(o=Test Organisation)(objectclass=athenOrganisation))")
        assert res[0]['status'] == 'P'
        # real nonce: crack open the PostScript file and grab the nonce
        with open(config.latex_path+'/'+'test.organisation.ps','r') as fd: psfile = fd.read()
        real_nonce = re.search(r"Fa\(([A-Z0-9]{10})\)",psfile).group(1)
        logging.debug("using real nonce now %r" % real_nonce)
        rv = self.app.post("/config/confirm",data=dict(
            nonce=real_nonce,
            uid="test.organisation"),follow_redirects=True)
        logging.debug(repr(rv.data))
        assert b" has been validated" in rv.data
        res = l.query(query="(&(o=Test Organisation)(objectclass=athenOrganisation))")
        assert res[0]['status'] == 'C'

    def test_nslcd(self):
        """test that on this system LDAP users are accessible with the 
           Name Service Switch
        """
        # random suffix to defeat nslcd cache
        suffix = "".join(random.choice("".join(chr(i) for i in range(ord('a'),ord('z')))) for _ in range(0,5))
        # first should bork on non-existent account
        with self.assertRaise(KeyError):
            pwd.getpwnam("test.org."+suffix)
        self.make_org("Test Org "+suffix)
        time.sleep(1) # give LDAP changes chance to become visible to nslcd
        # and now it should work. UID will vary as our teardowns don't reset the counter.
        r = pwd.getpwnam("test.org."+suffix)
        assert r.pw_gid == 2000
        assert r.pw_dir == '/home/athen/home/test.org.'+suffix
    
    def test_delivery(self):
        self.make_org()
        rv = self.app.post("/config/user/save",data=dict(
            givenName="Ian",
            sn="Haywood",
            medicalSpecialty="psychiatrist",
            providerNumber="246564AK"),follow_redirects=True)
        outmsg = MIMEMultipart()
        outmsg['From'] = 'Ian Haywood <ihaywood3@gmail.com>'
        outmsg['To'] = 'Ian Haywood <ihaywood3@gmail.com>'
        outmsg['Subject'] = 'Test messages'
        outmsg["Message-Id"] = email.utils.make_msgid(domain=config.domain)
        outmsg['Date'] = email.utils.formatdate()
        mt = MIMEText("This is the body")
        mt['Content-Disposition'] = 'inline'
        outmsg.attach(mt)
        email1 = '''To: Ian Haywood <test.organisation@{}>
From: Ian Haywood <ian@haywood.id.au>
Subject: [Bloggs, John (M) DOB: 1/12/1979] test message
Message-ID: <msg1@localhost>
Date: Fri, 8 Sep 2017 12:10:20 +1000
MIME-Version: 1.0
Content-Type: text/plain
Content-Transfer-Encoding: 7bit

this is a plain test message.

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
'''
        uctx = {"UID":os.getuid(),
                "USER":"test.organisation",
                "REALNAME":"Test Organisation",
                "GID":os.getgid(),
                "HOME":os.environ["HOME"],
                "deliveryFormat":["pit-ft"]
                }
        email1 = email1.format(config.domain)
        msg = email.message_from_string(email1)
        backward, box, onward = accounting.received_filter(msg)
        udb = userdb.UserDB()
        onward = mailfilter.process(uctx, onward, udb)
        outmsg.attach(self.extract_attachment(onward))
        # FIXME: examine the message/check the userDB
        email2 = '''To: Ian Haywood <test.organisation@{}>
From: Ian Haywood <ian@haywood.id.au>
Subject: [Bloggs, John (M) DOB: 1/12/1979] test message
Message-ID: <msg2@localhost>
Date: Fri, 8 Sep 2017 12:10:20 +1000
MIME-Version: 1.0
Content-Type: text/html
Content-Transfer-Encoding: 7bit

<html><body><p>
This message has some basic formatting. This should be in <b>bold</b>. This should be <u>underlined</u>. This should
be a <a href="http://ozdocit.org/cgi-bin/mailman/listinfo/nat-div">web link</a>. </p>

<h2>This is a header: bold and 14-point</h2>

<p>
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
</p>
</body></html>
'''
        for df in ['pit-rtf','hl7-oru-ft','hl7-oru-rtf','hl7-ref-ft','hl7-ref-rtf']:
            uctx['deliveryFormat'] = [df]
            email2 = email2.format(config.domain)
            msg = email.message_from_string(email2)
            backward, box, onward = accounting.received_filter(msg)
            udb = userdb.UserDB()
            onward = mailfilter.process(uctx, onward, udb)
            print(onward.as_string())
            outmsg.attach(self.extract_attachment(onward))
        with open("outmsg.eml","w") as fd:
            fd.write(outmsg.as_string())

    def extract_attachment(self,msg):
        for part in msg.walk():
            if part['Content-Disposition']:
                if part['Content-Disposition'].startswith('attachment'):
                    return part
        
        
        
if __name__ == '__main__':
    unittest.main(verbosity=2,defaultTest='theTestCase.test_delivery')
