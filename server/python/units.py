#!env python3
import os, os.path, sys, time, pudb, unittest, subprocess, sys, re
from unittest import skip
import logging
sys.path.append("../../lib")

import myldap, config, control, server

class OneTestCase(unittest.TestCase):

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
        if os.path.exists("/home/athen/home/test.organisation/"):
            os.system("sudo rmdir /home/athen/home/test.organisation/")
            os.system("sudo rm /home/athen/home/test.organisation.img")
            os.system("sudo rm -Rf /home/vmail/spool/test.organisation/")
            os.system("sudo rm -f %s/test.organisation.ps" % config.latex_path)
            #os.system("sudo userdel test.organisation")

            
    def delete_all_ldap(self):
        with myldap.LDAP(dn=config.ldap_user,password=config.password) as l:
            for i in l.query(query="(objectClass=athenPerson)",fields=["cn"]):
                i.delete()
            for i in l.query(query="(objectClass=athenOrganisation)",fields=["o"]):
                i.delete()
            
    def make_org(self,testing="yes"):
        rv = self.app.post("/config/acct/save",data=dict(
            type="O",
            userPassword="foobar123",
            userPassword_repeat="foobar123",
            o="Test Organisation",
            l="Werribee",
            postalCode="3030",
            businessCategory="general practice",
            street="1 Foo St",
            st="Victoria",
            telephoneNumber="97421111",
            _testing=testing
        ),follow_redirects=True)
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

if __name__ == '__main__':
    unittest.main()
