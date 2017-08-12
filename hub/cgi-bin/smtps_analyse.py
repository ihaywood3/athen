#!/usr/bin/python

# analyses a set of emails and maintains a big databse of all the SMTPS SSL certs
# This file is part of ATHEN.
# ATHEN is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# ATHEN is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with ATHEN.  If not, see <http://www.gnu.org/licenses/>.

# requirements: python-dnspython, psycopg2, pyOpenSSL (pip)

import threading, dns, socket, smtplib, ssl, sys, dns.exception, dns.resolver, os, sys, os.path
import logging, email, email.utils, datetime, time, hashlib, mailbox, re
logging.basicConfig(level=logging.DEBUG)
from Queue import Queue
from threading import Thread

import psycopg2
from OpenSSL import crypto

from cryptography.hazmat.primitives.serialization import PublicFormat, Encoding

#db = psycopg2.connect(database='smtps',user='ian')
running = set()

def query(q,params=()):
    try:
        cur = db.cursor()
        cur.execute(q,params)
        r = cur.fetchall()
        cur.close()
        return r
    except:
        db.rollback()
        raise

def sql(q):
    try:
        cur = db.cursor()
        cur.execute(q)
        cur.close()
    except:
        db.rollback()
        raise
    else:
        db.commit()


def x509_name(x509):
    return "/".join([i+'='+j for i, j in x509.get_components()])

"""do an MX lookup"""
def mxlookup(domain):
    try:
        logging.info("resolving %s" % domain)
        r = list(dns.resolver.query(domain,'MX'))
        #r.sort(key=lambda x: x.preference)
        for i in r:
            yield (i.exchange, i.preference)
    except dns.exception.DNSException:
        logging.error("Couldn't find MX entry for %s" % domain)
        return

def test_smtps(exchange):
    try:
        smtp = smtplib.SMTP()
        smtp.connect(str(exchange))
        smtp.starttls()
        try:
            bin_cert = smtp.sock.getpeercert(True)
        except:
            smtp.quit()
            return ("No actual SSL connection",None)
        smtp.quit()
        if bin_cert is None:
            return ("No certificate provided",None)
        #raw_cert = ssl.DER_cert_to_PEM_cert(bin_cert)
        return ("SUCCESS",bin_cert)
    except (smtplib.SMTPException,socket.error) as exc:
        return ("SMTP connection FAILED: %s" % str(exc),None)
    except socket.timeout:
        return ("SMTP connection FAILED: timeout",None)

def analyse_exchange(mxdomain,preference,exchange):
    logging.info("analysing exchange %s" % exchange)
    status, bin_cert = test_smtps(exchange)
    logging.info("result %r for %s" % (status,exchange))
    if status == "SUCCESS":
        cert = crypto.load_certificate(crypto.FILETYPE_ASN1, bin_cert)
        sha1 = cert.digest('SHA1')
        r = query("select 1 from exchanges where cert_sha1='%s' and exchange='%s'" % (sha1,exchange))
        if len(r) == 0:
            pem = ssl.DER_cert_to_PEM_cert(bin_cert)
            validto = cert.get_notAfter()
            validto = validto[0:4]+'-'+validto[4:6]+'-'+validto[6:8]
            rawkey = cert.get_pubkey().to_cryptography_key().public_bytes(Encoding.DER,PublicFormat.PKCS1)
            h = hashlib.sha1()
            h.update(rawkey)
            sql("insert into exchanges (mx,exchange,preference,status,cert_sha1,issuer,subject,validto,pem,pubkey_sha1) values ('%s','%s',%s,'SUCCESS','%s',$$%s$$,$$%s$$,'%s',$$%s$$,'%s')" % (
                mxdomain,
                exchange,
                preference,
                sha1,
                x509_name(cert.get_issuer()),
                x509_name(cert.get_subject()),
                validto,
                pem,
                h.hexdigest()
            ))
    else:
        r = query("select 1 from exchanges where mx='%s' and exchange='%s'" % (mxdomain,exchange))
        if len(r) == 0:
            sql("insert into exchanges(status,preference,mx,exchange) values ($$%s$$,%s,$$%s$$,$$%s$$)" % (status,preference,mxdomain,exchange))
        else:
            sql("update exchanges set status=$$%s$$ where preference=%s and mx='%s' and exchange='%s'" % (status,preference,mxdomain,exchange))

class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()
        
    def run(self):
        while True:
            cmd, args = self.tasks.get()
            try:
                cmd(*args)
            except Exception as e:
                logging.exception("thread failed")
            finally:
                self.tasks.task_done()

pool = Queue(20)
for _ in range(20): Worker(pool)

def analyse_domain(mxdomain,force=False):
    go_ahead = False
    r = query("select age(lastchecked) > '6 month'::interval from domains where mx='%s'" % mxdomain)
    if len(r) == 1:
        if r[0][0] or force:
            go_ahead = True
            sql("update domains set lastchecked=now() where mx='%s'" % mxdomain)
        else:
            pass
            #logging.info("ignoring %s as recently done" % mxdomain)
    else:
        go_ahead = True
        sql("insert into domains(mx) values ('%s')" % mxdomain)
    if go_ahead:
        for exchange, preference in mxlookup(mxdomain):
            r = query("select mx, exchange, cert_sha1 from exchanges where exchange ilike '%s' and mx <> '%s'" % (exchange, mxdomain))
            if len(r) > 0:
                logging.info("we already know about %s from %s, ignoring" % (exchange, r[0][0]))
            else:
                #analyse_exchange(mxdomain,preference,exchange)
                pool.put((analyse_exchange,(mxdomain,preference,exchange)))

def analyse_emails(d):
    for i in os.listdir(d):
        with open(os.path.join(d,i)) as fp:
            msg = email.message_from_file(fp)
        analyse_email(msg)

def analyse_email(msg):
    all_addrs = []
    for j in ["To","From","Cc","Bcc","Reply-To"]:
        if j in msg:
            all_addrs.extend(email.utils.getaddresses(msg.get_all(j,[])))
    for real, addr in all_addrs:
        addr = addr.split("@")
        if len(addr) == 2:
            mxdomain = addr[1]
            mxdomain = mxdomain.replace("'","")
            if not mxdomain in running:
                running.add(mxdomain)
                pool.put((analyse_domain,(mxdomain,)))

def analyse_mboxes(d):
    for i in os.listdir(d):
        thebox = mailbox.mbox(os.path.join(d,i))
        for msg in thebox:
            analyse_email(msg)


def analyse_log(logs):
#Oct  3 08:03:25 haywood postfix/qmgr[9871]: 738DD8212D: from=<5db38c9.a36812.49315822.1@mbounces.com>, size=34156, nrcpt=1 (queue active)
    #regexp = re.compile(r"^([A-Za-z]+) +[0-9]+ +[0-9:]+ haywood postfix/qmgr\[[0-9]+\]: [0-9A-F]+: from=<[^@]+@(.+)>, size=")
    in_conn_re = re.compile(r"postfix/smtpd\[[0-9]+\]: [0-9A-F]+: client=(.+)") # , sasl_method=
    in_tls_re = re.compile(r"TLS connection established from (.*): ")
    out_tls_re = re.compile(r"TLS connection established to (.*): ")
    out_conn_re = re.compile(r"relay=(.*), delay=")
    the_month = time.strftime("%b")
    stats = {}
    for fname in logs:
        with open(fname,"r") as fd:
            for l in fd.readlines():
                index = -1
                m = in_conn_re.search(l)
                if m and not ("sasl_method=" in l):
                    index = 0
                else:
                    m = in_tls_re.search(l)
                    if m:
                        index = 1
                    else:
                        m = out_conn_re.search(l)
                        if m:
                            index = 2
                        else:
                            m = out_tls_re.search(l)
                            if m:
                                index = 3
                if m and index > -1:
                    host = m.group(1)
                    if not host in stats:
                        stats[host] = [0, 0, 0, 0]
                    stats[host][index] += 1
    for domain in stats.keys():
        st = stats[domain]
        print "{:<40}{:>5}{:>5}{:>5}{:>5}".format(domain[:40],st[0],st[1],st[2],st[3])

if __name__ == '__main__':
    analyse_log(['/var/log/mail.log'])

def oldmain():
    cmd = sys.argv[1]
    if cmd == 'scan':
        analyse_emails(sys.argv[2])
    if cmd == 'mbox':
        analyse_mboxes(sys.argv[2])
    if cmd == 'fix':
        r = query("select mx, preference, exchange from exchanges where status <> 'SUCCESS'")
        for i in r:
            sql("delete from exchanges where mx='%s' and exchange='%s' and status <> 'SUCCESS'"  % (i[0],i[2]))
            logging.info("re-analysing exchange %s" % i[2])
            pool.put((analyse_exchange,(i[0],i[1],i[2])))
    if cmd == 'logs':
        analyse_logs(sys.argv[2:])
    pool.join()

