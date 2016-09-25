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

import threading, dns, socket, smtplib, ssl, sys, dns.exception, dns.resolver, os, sys
import logging, email, email.utils, datetime, time
import psycopg2
from OpenSSL import crypto

db = psycopg2.connect(database='smtps',user='ian')

def query(q,params=()):
    cur = db.cursor()
    cur.execute(q,params)
    r = cur.fetchall()
    cur.close()
    return r

def sql(q):
    cur = conn.cursor()
    cur.execute(q)
    cur.close()
    conn.commit()



"""do an MX lookup"""
def mxlookup(domain):
    try:
        r = list(dns.resolver.query(domain,'MX'))
        #r.sort(key=lambda x: x.preference)
        for i in r:
            logging.info("MX found %r %r" % (i.exchange, i.preference))
            yield (i.exchange, i.preference)
    except dns.exception.DNSException:
        logging.error("Couldn't find MX entry for %s" % domain)
        return

def test_smtps(exchange):
    try:
        smtp = smtplib.SMTP()
        smtp.connect(str(exchange))
        smtp.starttls()
        bin_cert = smtp.sock.getpeercert(True)
        smtp.quit()
        if bin_cert is None:
            return ("No certificate provided",None)
        #raw_cert = ssl.DER_cert_to_PEM_cert(bin_cert)
        return ("SUCCESS",bin_cert)
    except (smtplib.SMTPException,socket.error) as exc:
        return ("SMTP connection FAILED: %s" % str(exc),None)
    except socket.timeout:
        return ("SMTP connection FAILED: timeout",None)

def analyse_domain(mxdomain):
    go_ahead = False
    r = query("age(lastchecked) > '6 month'::interval from domains where mx='%s'" % mxdomain)
    if len(r) == 1:
        if r[0]:
            go_ahead = True
            sql("update domains set lastchecked=now() where mx='%s'" % mxdomain)
    else:
        go_ahead = True
        sql("insert into domains(mx) values ('%s')" % mxdomain)
    if go_ahead:
        for exchange, preference in mxlookup(mxdomain):
            status, bin_cert = test_smtps(exchange)
            if status == "SUCCESS":
                cert = crypto.load_certificate(crypto.FILETYPE_ASN1, bin_cert)
                sha1 = cert.digest('SHA1')
                r = query("select 1 from exchanges where sha1='%s' and exchange='%s'" % (sha1,exchange))
                if len(r) == 0:
                    pem = ssl.DER_cert_to_PEM_cert(bin_cert)
                    validto = cert.get_notAfter()
                    validto = validto[0:4]+'-'+validto[4:6]+'-'+validto[6:8]
                    sql("insert into exchanges (mx,exchange,preference,status,sha1,issuer,subject,validto,pem) values ('%s','%s',%s,'SUCCESS','%s','%s','%s','%s',$$%s$$)" % (
                        mxdomain,
                        exchange,
                        preference,
                        sha1,
                        x509_name(cert.get_issuer()),
                        x509_name(cert.get_subject()),
                        validto,
                        pem
                    ))
            else:
                r = query("select 1 from exchanges where preference=%s and mx=%s and exchange=%s" % (preference,mxdomain,exchange))
                if len(r) == 0:
                    sql("insert into exchanges(status,preference,mx,exchange) values ('%s',%s,'%s','%s')" % (status,preference,mxdomain,exchange))
                else:
                    sql("update exchanges set status='%s' where preference=%s and mx='%s' and exchange='%s'" % (status,preference,mxdomain,exchange))

def analyse_emails(dir):
    for i in os.listdir(dir):
        with open(i) as fp:
            msg = email.message_from_file(fp)
        all_addrs = []
        for j in ["To","From","Cc","Bcc","Reply-To"]:
            if j in msg:
                all_addrs.extend(email.utils.getaddresses(msg.get_all(i,[])))
        for real, addr in all_addrs:
            addr = addr.split("@")
            if len(addr) == 2:
                analyse_domain(addr[1])



#f __name__ == '__main__':
#   cmd = sys.argv[1]
            #if cmd == 'scan':
        #analyse_emails(sys.argv[2])

import pudb
pudb.set_trace()
analyse_domain("haywood.id.au")
