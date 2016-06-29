# a basic library for storing private user-specific data in a SQLite database
# (i.e. not part of the public LDAP store)

import config, util
import sqlite3
import os, os.path



db_exists = os.path.exists(config.sql_path)
db = sqlite3.connect(config.sql_path)

if not db_exists:
    cur = db.cursor()
    cur.execute("""create table users (
    uid text,
    nonce text,
    crypted boolean,
    password text)""")
    cur.close()
    db.commit()

def add_user(uid,nonce,encrypted,password):
    cur = db.cursor()
    cur.execute("insert into users (uid, nonce, crypted, password) values (?, ?, ?, ?)", (uid,nonce,encrypted,password))
    cur.close()
    db.commit()

def get_user_attr(uid,thing):
    cur = db.cursor()
    cur.execute("select {} from users where uid=?".format(thing),(uid,))
    r = cur.fetchone()
    if r is None:
        raise Exception("no such user {}".format(uid))
    r = r[0]
    cur.close()
    return r

class User:
    """General worker class for user-specific actions
    sits in a session object most of the time
    """
    def __init__(self, uid):
        self.uid = uid

    def user_exists(self):
        cur = db.cursor()
        cur.execute("select 1 from users where uid=?",(self.uid,))
        r = len(cur.fetchall()) > 0
        cur.close()
        return r
        
    def add(self,nonce,encrypted,passwd):
        add_user(self.uid,nonce,encrypted,passwd)

    def get(self,thing):
        return get_user_attr(self.uid,thing)
        
    def login(self,entered_password):
        """False is login unsuccessful"""
        stored_passwd  = get_user_attr(self.uid,'password')
        hashed_password = util.make_hash(entered_password,stored_password)
        if hashed_password != stored_password:
            return False
        self.owner = False
        if self.uid == config.owner:
            self.owner = True
        return True


    


