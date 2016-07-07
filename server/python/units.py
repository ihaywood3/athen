import os
import server
import store
import unittest
import tempfile

import sys
sys.path.append("../../lib")
import myldap, config

class OneTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_name = tempfile.mkstemp()
        server.app.config['TESTING'] = True
        self.app = server.app.test_client()
        with server.app.app_context():
            store.init_db(debug=True,sql_path=self.db_name)

    def tearDown(self):
        self.delete_all_ldap()
        os.close(self.db_fd)
        os.unlink(self.db_name)
        
    def delete_all_ldap(self):
        l = myldap.LDAP(local=True,password=config.password)
        for i in l.query(query="(objectClass=athenUser)",fields=["cn"]):
            i.delete()
        for i in l.query(query="(objectClass=athenOrganisation)",fields=["o"]):
            i.delete()
            
    def test_make_org(self):
        rv = self.app.post("/org/save",data=dict(
            userPassword="foobar123",
            userPassword_repeat="foobar123",
            o="Test Organisation",
            l="Werribee",
            postalCode="3030",
            businessCategory="general practice",
            street="1 Foo St",
            st="Victoria",
            mail="foo",
            telephoneNumber="97421111"
        ),follow_redirects=True)
        assert "New organisation saved successfully" in rv

if __name__ == '__main__':
    unittest.main()