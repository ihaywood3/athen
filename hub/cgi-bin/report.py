#!/usr/bin/python

# analyses a remmote server and issues a report on it
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

import threading, dns, socket, smtplib, ssl, sys, dns.exception, dns.resolver


"""do an MX lookup"""
def mxlookup(domain):
    try:
        r = list(dns.resolver.query(domain,'MX'))
        r.sort(key=lambda x: x.preference)
        for i in r:
            print 'found MX %s %s' % (i.preference, i.exchange)
            try:
                ip6 = dns.resolver.query(str(i.exchange), 'AAAA')
                addr = str(ip6[0])
                print "found IPv6 address %s" % addr
                family = socket.AF_INET6
                return (addr, family, str(i.exchange))
            except dns.exception.DNSException:
                try:
                    ip4 = dns.resolver.query(str(i.exchange), 'A')
                    addr = str(ip4[0])
                    print "found IPv4 address %s" % addr
                    family = socket.AF_INET
                    return (addr, family, str(i.exchange))
                except dns.exception.DNSException:
                    print "Couldn't find a working A/AAAA entry for %s" % i.exchange
        print "Couldn't find any working entries for %s" % domain
        return None
    except dns.exception.DNSException:
        print "Couldn't find MX entry for %s" % domain
        return None
    #except:
    #    e = sys.exc_info()[0]
    #    print "Could find MX entry for %s: %s" % (domain,e)
    #    return None
    
def test_port(addr, family, port, portname):
    try:
        s = socket.socket(family, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((addr, port))
        s.close()
        print "%s connected SUCCESS" % portname
    except socket.error as err:
        print "%s connection FAILED: %s" % (portname, str(err))
    except socket.timeout:
        print "%s connection FAILED: timeout" % portname
    except:
        e = sys.exc_info()[0]
        print "%s connection FAILED: unknown reason: %s" % (portname, e)

def test_smtps(exchange):
    try:
        smtp = smtplib.SMTP()
        smtp.connect(str(exchange))
        smtp.starttls()
        remote_cert = ssl.DER_cert_to_PEM_cert(smtp.sock.getpeercert(True))
        print remote_cert
        smtp.quit()
        print "SMTP connected SUCCESS"
    except (smtplib.SMTPException,socket.error) as exc:
        print "SMTP connection FAILED: %s" % str(exc)
    except socket.timeout:
        print "SMTP conenction FAILED: timeout"
    #except:
    #    e = sys.exc_info()[0]
    #    print "SMTP connection failed: %s" % str(e)
    
def test_domain(domain):
    mx = mxlookup(domain)
    if not mx is None:
        addr, family, exchange = mx
        ports = [(80,"Web"), (443, "Secure Web"), (993, "Secure IMAP"), (587, "Mail Submission")]
        threads = [threading.Thread(target=test_port,args=(addr, family, port, portname)) for port, portname in ports]
        for t in threads: t.start()
        test_smtps(exchange)
        for t in threads: t.join()


if __name__ == '__main__':
    test_domain('haywood.id.au')
        
