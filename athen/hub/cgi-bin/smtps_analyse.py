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

db = psycopg2.connect(database='smtps',user='ian')
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
        logging.debug("resolving %s" % domain)
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
        return ("SUCCESS",bin_cert)
    except (smtplib.SMTPException,socket.error) as exc:
        return ("SMTP connection FAILED: %s" % str(exc),None)
    except socket.timeout:
        return ("SMTP connection FAILED: timeout",None)

def analyse_exchange(mxdomain,preference,exchange):
    logging.debug("analysing exchange %s" % exchange)
    status, bin_cert = test_smtps(exchange)
    logging.debug("result %r for %s" % (status,exchange))
    if status == "SUCCESS":
        cert = crypto.load_certificate(crypto.FILETYPE_ASN1, bin_cert)
        sha1 = cert.digest('SHA1')
        rawkey = cert.get_pubkey().to_cryptography_key().public_bytes(Encoding.DER,PublicFormat.PKCS1)
        h= hashlib.sha1()
        h.update(rawkey)
        pubkey_sha1 = h.hexdigest()
        validto = cert.get_notAfter()
        validto = validto[0:4]+'-'+validto[4:6]+'-'+validto[6:8]
    else:
        sha1 = "FAILED"
    r = query("select status,cert_sha1,pubkey_sha1,issuer,subject from exchanges where mx='%s' and exchange='%s' order by created desc" % (mx,exchange))
    if len(r) == 0:
        logging.info("%s (%s): new exchange status %r" % (exchange,mxdomain,status))
        if status == 'SUCCESS':
            logging.info("new certificate issuer %r subject %r validto %s" % (x509_name(cert.get_issuer()),x509_name(cert.get_subject()),validto))
    else:
        oldstatus, old_cert_sha1, old_pubkey, old_isser, old_subject = r[0]
        if status == oldstatus:
            if status == "SUCCESS":
                if old_cert_sha1 == sha1:
                    logging.debug("%s (%s): certificate unchanged" % (exchanged,mxdomain))
                    return
                else:
                    if old_pubkey == pubkey_sha1:
                        logging.info("%s (%s): certificate changed but pubkey unchanged")
                    else:
                        logging.warn("%s (%s): certificate pubkey has changed")
                    logging.info("old certificate issuer %r subject %r" % (old_isser, old_subject))
                    logging.info("new certificate issuer %r subject %r validto %s" % (x509_name(cert.get_issuer()),x509_name(cert.get_subject()),validto))
            else:
                logging.debug("%s (%s): status unchanged %r" % (exchange,mxdomain,status))
                return
        else:
            if status == 'SUCCESS':
                logging.info("%s (%s): exchange now has SSL was %r" % (exchange,mxdomain,oldstatus))
                logging.info("new certificate issuer %r subject %r validto %s" % (x509_name(cert.get_issuer()),x509_name(cert.get_subject()),validto))
            elif oldstatus == 'SUCCESS':
                logging.warn("%r (%s): was SSL now status %r" % (exchange, mxdomain, status))
            else:
                logging.warn("%r (%s): status was %r now status %r" % (exchange, mxdomain, oldstatus, status))
    if status == 'SUCCESS':
        sql("insert into exchanges (mx,exchange,preference,status,cert_sha1,issuer,subject,validto,pem,pubkey_sha1) values ('%s','%s',%s,'SUCCESS','%s',$$%s$$,$$%s$$,'%s',$$%s$$,'%s')" % (
            mxdomain,
            exchange,
            preference,
            sha1,
            x509_name(cert.get_issuer()),
            x509_name(cert.get_subject()),
            validto,
            ssl.DER_cert_to_PEM_cert(bin_cert),
            pubkey_sha1
            ))
    else:
        sql("insert into exchanges (mx,exchange,preference,status) values ('%s','%s',%s,'%s','%s')" % (
            mxdomain,
            exchange,
            preference,
            status))
  
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

def analyse_domain(mxdomain):
    r = query("select 1 from domains where mx='%s'" % mxdomain)
    if len(r) == 1:
        sql("update domains set lastchecked=now() where mx='%s'" % mxdomain)
    else:
        logging.info("new domain %r" % mxdomain)
        sql("insert into domains(mx) values ('%s')" % mxdomain)
    for exchange, preference in mxlookup(mxdomain):
        analyse_exchange(mxdomain,preference,exchange)


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


def analyse_log2(logfile):
    # Sep 18 00:35:51 haywood postfix/smtp[13747]: C99A580789: to=<admin@jager.net.au>, relay=mx4.netregistry.net[202.124.241.196]:25, delay=17, delays=0.16/0.01/4.7/12, dsn=2.0.0, status=sent (250 OK id=1dtiA9-0000co-1B)
    regexp = re.compile(r"^([A-Za-z]+) +[0-9]+ +[0-9:]+ haywood postfix/smtp\[[0-9]+\]: [0-9A-F]+: to=<[^@]+@(.+)>, ")
    alldomains = set()
    with open(logfile,"r") as fd:
        for l in fd:
            m = regexp.match(l)
            if m:
                alldomains.add(m.group(1))
    for i in sorted(list(alldomains)):
        analyse_domain(i)

if __name__ == '__main__':
    analyse_log2('/var/log/mail.log')
