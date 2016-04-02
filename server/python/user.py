import config
import util

class User:
    """General worker class for user-specifc actions
    sits in a session object most of the time
    """
    def __init__(self):
        self.dn = None
        self.owner = False
        
    def login(self,username,password):
        """False is login unsuccessful"""
        res = g.ldap.query(config.base_dn,"(&{objectclass=athenOrganisation)(o=%s))",username,node=True,fields=["o","userPassword"])
        if len(res) == 0:
            return False
        res = res[0]
        ldap_passwd  = res['userPassword']
        hashed_password = util.make_hash(entered_password,ldap_password)
        if hashed_password != ldap_password:
            return False
        self.dn = res['dn']
        self.username = username
        self.owner = False
        if username == config.owner:
            self.owner = True

    
