#!/usr/bin/python3
"""
A manager class for a per-user SQLIte database
storing detials of sent mails and other data
"""

import os, os.path, sqlite3, re, logging
import util
from email.utils import parseaddr

logger = logging.getLogger(__name__)

MAXLOGDAYS=120 

class UserDB(object):

    # Borgify this object
    def __new__(cls, *p, **k):
        if not '_the_instance' in cls.__dict__:
            cls._the_instance = object.__new__(cls)
            cls._the_instance.db = None
            cls._the_instance.current_message = None
            logger.debug("setting bufffer to []")
            cls._the_instance.buffer = []
        return cls._the_instance


    def __need_db(self):
        if self.db is None:
            dbpath = os.path.join(os.environ['HOME'],"data.sqlite")
            self.db = sqlite3.connect(dbpath)
            cur = self.db.cursor()
            try:
                cur.execute("select 1 from messages limit 1")
            except sqlite3.OperationalError:
                cur.execute("""
                create table messages (
                    fname text,
                    message_id text,
                    status text,
                    outgoing integer,
                    email text,
                    name text,
                    subject text,
                    stamp text default current_timestamp);""")
                cur.execute("""
                create table senders (
                   email text,
                   run_no text,
                   initials text
                );""")
                cur.execute("""
                create table log (logtime text default CURRENT_TIMESTAMP, 
                                  logtext text, 
                                  extra text, 
                                  level integer, 
                                  messages_rowid integer);
    """)
                cur.execute("""
                create table patients (surname text, 
                                       firstname text,
                                       birthdate date);
                """)
                cur.close()
                self.db.commit()
            else:
                # trim the log
                cur.execute("delete from log where julianday('now') - julianday(logtime) > {}".format(MAXLOGDAYS))
                cur.execute("delete from messages where julianday('now') - julianday(stamp) > {}".format(MAXLOGDAYS))
                cur.close()

    def wipe_db(self):
        """For testing purposes only"""
        self.__need_db()
        cur = self.db.cursor()
        cur.execute("delete from senders")
        cur.execute("delete from messages")
        cur.execute("delete from log")
        cur.close()
        self.db.commit()

    def raw_query(self,query):
        self.__need_db()
        cur = self.db.cursor()
        cur.execute(query)
        res = cur.fetchall()
        cur.close()
        return res

    def get_patient_id(self, surname, firstname, birthdate):
        """
        Give us a local patient ID given the name and DOB
        HL7 requires this
        """
        self.__need_db()
        cur = self.db.cursor()
        surname = surname.upper()
        firstname = firstname.upper()
        cur.execute("select rowid from patients where surname = ? and firstname = ? and birthdate = ?",(surname,firstname,birthdate))
        row = cur.fetchone()
        if row:
            res = row[0]
        else:
            cur.execute("insert into patients(surname, firstname, birthdate) values (?, ?, ?)",(surname,firstname,birthdate))
            res = cur.lastrowid
            self.db.commit()
        cur.close()
        return res

    def make_initials(self, fullname):
        """
        Make initials from a human/institutional name using fixed rules
        (obviously this won't always be "right" as organisations can
        make acronyms in different ways, but for our use-case this doesn't matter
        it just needs to have some guessable connection to the name)

        >>> udb = UserDB()
        >>> udb.make_initials("Ian Haywood")
        'IHA'
        >>> udb.make_initials("Royal Melbourne Hospital")
        'RMH'
        >>> udb.make_initials("Austin Hospital")
        'AUS'
        >>> udb.make_initials("Ninox Clinic")
        'NIN'
        >>> udb.make_initials("Foo Pty Ltd")
        'FOO'
        >>> udb.make_initials("Telstra")
        'TEL'
        >>> udb.make_initials("Stupid 6word")
        'SZW'
        >>> udb.make_initials("five words in a row")
        'FWI'
        """
        names = fullname.upper().strip().split()
        if len(names) == 2:
            if names[1] == "CLINIC": del names[1]
            elif names[1] == "HOSPITAL": del names[1]
        if len(names) >= 3 and names[-1] == "LTD" and names[-2] == "PTY":
            del names[-1]
            del names[-1]
        if len(names) >= 3:
            initials = names[0][0]+names[1][0]+names[2][0]
        elif len(names) == 1:
            initials = names[0][:3]
        else:
            initials = names[0][0]+names[1][:2]
        initials = re.sub("[^A-Z]","Z",initials)
        return initials

    def inc_initials(self, initials):
        """
        Alphabetically increment a 3-letter initial
        (to avoid collisions in people/institions with similar initials

        >>> udb = UserDB()
        >>> udb.inc_initials("ABC")
        'ABD'
        >>> udb.inc_initials("AZZ")
        'BAA'
        >>> udb.inc_initials("ZZZ")
        'AAA'
        """
        a = list(initials)
        if a[2] == 'Z':
            if a[1] == 'Z':
                if a[0] == 'Z':
                    a[0] = 'A'
                else:
                    a[0] = chr(ord(a[0])+1)
                a[1] = 'A'
            else:
                a[1] = chr(ord(a[1])+1)
            a[2] = 'A'
        else:
            a[2] = chr(ord(a[2])+1)
        return "".join(a)

    def get_run_from_sender(self, sender, fullname=None, incr_run_no=True):
        """
        get a "run number" and 3-letter initials from the sender info
        Guaranteed to be unique 
        (which is why this is a method of UserDB and not in lib/util.py: 
        because we need a record of what's come before
        Used to generate unique DOS-style 8.3 filenames where required
        (sadly still de rigueur for medical messaging)
        and for the "run number" field in PIT messages, also limited to
        5 digits.

        >>> udb = UserDB()
        >>> udb.wipe_db()
        >>> udb.get_sender("ian@haywood.id.au","Ian Haywood")
        (0, 'IHA')
        >>> udb.get_sender("ian@haywood.id.au","Ian Haywood")
        (1, 'IHA')
        >>> udb.get_sender("ian2@haywood.id.au","Ian Haywood")
        (0, 'IHB')
        >>> udb.get_sender("ian2@haywood.id.au","Ian Haywood")
        (1, 'IHB')
        """
        self.__need_db()
        if sender and not fullname:
            if type(sender) is list: sender = sender[0]
            fullname, sender = parseaddr(sender)
            if fullname == '': fullname = sender
        cur = self.db.cursor()
        cur.execute("select run_no, initials from senders where email = ?",(sender,))
        row = cur.fetchone()
        if row:
            run_no = int(row[0])
            initials = row[1]
            if incr_run_no:
                while True:
                    new_run_no = run_no+1
                    cur.execute("update senders set run_no=? where email=? and run_no=?",(new_run_no,sender,run_no))
                    if cur.rowcount == 0:
                        cur.execute("select run_no from senders where email = ?",(sender),)
                        run_no = row[0]
                    else:
                        run_no = new_run_no
                        break
                cur.close()
                self.db.commit()
            else:
                cur.close()
            return (run_no, initials)
        else:
            initials = self.make_initials(fullname)
            while True:
                cur.execute("select 1 from senders where initials = ?",(initials,))
                if cur.fetchone():
                    initials = self.inc_initials(initials)
                else:
                    break
            cur.execute("insert into senders (email, run_no, initials) values (?, 0, ?)",(sender, initials))
            cur.close()
            self.db.commit()
            return (0, initials)

    def update_messages(self,message_id,status,outgoing=None,fname=None,temail=None,name=None,subject=None):
        """
        >>> u = UserDB()
        >>> u.wipe_db()
        >>> u.update_messages("some@foo.com","PENDING")
        >>> u.raw_query("select status from messages")[0]
        ('PENDING',)
        >>> u.update_messages("some@foo.com","FAILED")
        >>> u.get_messages_by_status("FAILED")
        [{...'message_id': 'some@foo.com'...}]
        """
        self.__need_db()
        cur = self.db.cursor()
        assert status in ['SENT','OK','FAILED','PENDING']
        if fname:
            # match by message_id AND filename (for emails with multiple files)
            cur.execute("select rowid, status from messages where message_id = ? and fname = ?",(message_id,fname))
        else:
            cur.execute("select rowid, status from messages where message_id = ?",(message_id,))
        row = cur.fetchone()
        clauses = []
        args = []
        if row:
            current_message = row[0]
            oldstatus = row[1]
            clauses = ['status=?',"stamp=datetime('now')"]
            args= [status]
        else:
            cur.execute("insert into messages (message_id,status) values (?, ?)",(message_id,status))
            current_message = cur.lastrowid
            oldstatus = None
        if self.current_message is None:
            self.current_message = current_message
            self.flush()
        else:
            self.current_message = current_message
        if row and oldstatus == "FAILED" and status != "FAILED":
            logger.debug("trying to set status to %r from FAILED, not allowed" % status)
            args = ['FAILED']
        if not outgoing is None:
            clauses.append("outgoing=?")
            args.append(outgoing)
        if name:
            clauses.append("name=?")
            args.append(name)
        if fname:
            clauses.append("fname=?")
            args.append(fname)
        if temail:
            clauses.append("email=?")
            args.append(temail)
        if subject:
            clauses.append("subject=?")
            args.append(subject)
        args.append(self.current_message)
        if clauses:
            cur.execute("update messages set {} where rowid=?".format(",".join(clauses)),args)
        cur.close()
        logger.debug("status set to {}".format(status))
        
    def get_messages_by_status(self,status):
        self.__need_db()
        cur = self.db.cursor()
        cur.execute("select message_id, fname, stamp, email, name, subject from messages where status=?",(status,))
        res = [{'message_id':i[0],'fname':i[1],'stamp':i[2],'email':i[3],'name':i[4],'subject':i[5]} for i in cur.fetchall()]
        cur.close()
        return res


    def get_message_by_id(self, msgid=None):
        cur = self.db.cursor()
        if msgid is None:
            cur.execute("select message_id, fname, stamp, email, name, subject from messages where rowid=?",(self.current_message,))
        else:
            cur.execute("select message_id, fname, stamp, email, name, subject from messages where message_id=?",(msgid,))
        res = [{'message_id':i[0],'fname':i[1],'stamp':i[2],'email':i[3],'name':i[4],'subject':i[5]} for i in cur.fetchall()]
        cur.close()
        return res

    def insert_log_entry(self, logtext, extra, level):
        if self.current_message is None:
            self.buffer = self.buffer+[(logtext, extra, level)]
        else:
            self.write_log_entry(logtext, extra, level)

    def write_log_entry(self, logtext, extra, level):
        # Insert log record:
        self.__need_db()
        cur = self.db.cursor()
        cur.execute("insert into log (logtext, extra, level, messages_rowid) values (?, ?, ?, ?)", (logtext, extra, level, self.current_message))
        cur.close()
        self.db.commit()

    def flush(self):
        for i in self.buffer:
            self.write_log_entry(*i)
        self.buffer = []

    def flush_with_id(self, msgid):
        """set the message id for logging without updating status"""
        self.__need_db()
        cur = self.db.cursor()
        cur.execute("select rowid from messages where message_id=?",(msgid,))
        res = cur.fetchone()
        if res:
            self.current_message = res[0]
            self.flush()
        cur.close()
        
MAP_LEVELS={logging.DEBUG: 0, logging.INFO: 1, logging.ERROR: 2, logging.WARN: 2, logging.CRITICAL: 3, logging.FATAL: 3}

class SQLiteHandler(logging.Handler):
    """
    Logging handler for SQLite.
    Based on Vinay Sajip's DBHandler class (http://www.red-dove.com/python_logging.html)
                   VALUES (
                        '%(dbtime)s',
                        '%(name)s',
                        %(levelno)d,
                        '%(levelname)s',
                        '%(msg)s',
                        '%(args)s',
                        '%(module)s',
                        '%(funcName)s',
                        %(lineno)d,
                        '%(exc_text)s',
                        %(process)d,
                        '%(thread)s',
                        '%(threadName)s'
                   );
                   """

    def __init__(self, udb):
        logging.Handler.__init__(self)
        self.udb = udb

    def emit(self, record):
        # Use default formatting:
        logtext = self.format(record)
        level = MAP_LEVELS.get(record.levelno, 0)
        if record.exc_info:
            extra = logging._defaultFormatter.formatException(record.exc_info)
        else:
            extra = "{}({}):{}".format(record.module, record.funcName, record.lineno)
        self.udb.insert_log_entry(logtext, extra, level)

_udb = UserDB()
_root = logging.getLogger()
_root.addHandler(SQLiteHandler(_udb))


if __name__ == "__main__":
    try: os.unlink("/home/ian/data.sqlite")
    except: pass
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS)
