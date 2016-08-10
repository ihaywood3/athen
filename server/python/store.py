# a basic library for storing private user-specific data in a SQLite database
# (i.e. not part of the public LDAP store)

import config, util
import sqlite3, random, string
import os, os.path
import logging

def init_db(debug=False,sql_path=None):
    global dbfile
    if debug:
        dbfile = sql_path
    else:
        dbfile = config.sql_path
    db_exists = os.path.exists(dbfile)
    logging.debug("opening DB for first time at {}".format(dbfile))
    db = sqlite3.connect(dbfile)
    if not db_exists:
        logging.debug("creating DB")
        cur = db.cursor()
        cur.execute("""create table users (
        uid text,
        nonce text,
        crypted boolean,
        password text,
        status text,
        cookie text,
        redirect text,
        logintime text)""")
        cur.close()
        db.commit()

def get_user_by_cookie(cookie):
    db = sqlite3.connect(dbfile)
    cur = db.cursor()
    cur.execute("select uid from users where cookie=? and logintime > datetime('now','-1 day')",(cookie,))
    r = cur.fetchone()
    if r is None:
        return None
    u = User(r[0],db)
    cur.close()
    return u

def make_cookie():
    return ''.join(random.choice(string.ascii_uppercase+string.digits) for _ in range(10))

class User:
    """General worker class for user-specific actions
    sits in a session object most of the time
    """
    def __init__(self, uid, db=None):
        self.uid = uid
        if db is None:
            db = sqlite3.connect(dbfile)
        self.db = db
            

    def user_exists(self):
        cur = self.db.cursor()
        cur.execute("select 1 from users where uid=?",(self.uid,))
        r = len(cur.fetchall()) > 0
        cur.close()
        return r
        
    def add(self,nonce,encrypted,passwd):
        cur = self.db.cursor()
        cur.execute("insert into users (uid, nonce, crypted, password) values (?, ?, ?, ?)", (self.uid,nonce,encrypted,passwd))
        cur.close()
        self.db.commit()

    def get(self,thing):    
        cur = self.db.cursor()
        cur.execute("select {} from users where uid=?".format(thing),(self.uid,))
        r = cur.fetchone()
        if r is None:
            raise Exception("no such user {}".format(self.uid))
        r = r[0]
        cur.close()
        return r
        
    def login(self,entered_password):
        """False is login unsuccessful"""
        stored_password = self.get('password')
        hashed_password = util.make_hash(entered_password,stored_password)
        if hashed_password != stored_password:
            return False
        self.cookie = make_cookie()
        self.set_cookie(self.cookie)
        return True
    
    def set_cookie(self, cookie):
        cur = self.db.cursor()
        cur.execute("update users set logintime=datetime('now'),cookie=? where uid=?",(cookie,self.uid))
        cur.close()
        self.db.commit()
    
    def logout(self):
        cur = self.db.cursor()
        cur.execute("update users set cookie=null,logintime=null where uid=?",(self.uid,))
        cur.close()

    def dump_users(self):
        cur = self.db.cursor()
        cur.execute("select * from users")
        print repr(cur.fetchall())
        cur.close()

    def owner(self):
        return (self.uid == config.owner)
    


