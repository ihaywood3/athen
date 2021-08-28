from zope.interface import implementer

from OpenSSL.crypto import FILETYPE_PEM
from twisted.internet.ssl import (
    optionsForClientTLS,
    Certificate,
    PrivateCertificate,
    KeyPair,
)
from twisted.trial import unittest
from twisted.internet import reactor
from twisted.web.iweb import IPolicyForHTTPS
from twisted.web.client import Agent, ResponseFailed, readBody


@implementer(IPolicyForHTTPS)
class LoadClientCert:
    def __init__(self, hostmap, server_cert, client_cert, client_key):
        self.hostmap = hostmap
        with open(server_cert) as fd:
            self.server_cert = Certificate.loadPEM(fd.read())
        with open(client_cert) as fd:
            client_cert = Certificate.loadPEM(fd.read())
        with open(client_key) as fd:
            client_key = KeyPair.load(fd.read(), FILETYPE_PEM)
        self.client_cert = PrivateCertificate.fromCertificateAndKeyPair(
            client_cert, client_key
        )

    def creatorForNetloc(self, hostname, port):
        hostname = hostname.decode("ascii")
        if hostname in self.hostmap:
            hostname = self.hostmap[hostname]

        import pdb

        pdb.set_trace()
        return optionsForClientTLS(hostname, self.server_cert, self.client_cert)


def getPage(url, server_cert, client_cert, client_key, hostmap={}):
    a = Agent(reactor, LoadClientCert(hostmap, server_cert, client_cert, client_key))
    d = a.request(b"GET", url.encode("ascii"))

    def cb_getBody(response):
        return readBody(response)

    return d.addCallback(cb_getBody)


class HubTest(unittest.TestCase):
    def test_getpage(self):
        def cb_print(s):

            print(s)

        DIR = "/home/ian/athen/hub/"
        d = getPage(
            "https://localhost:8443/",
            DIR + "server.crt",
            DIR + "client.crt",
            DIR + "client.key",
            {"localhost": "mintbox"},
        )
        d.addCallback(cb_print)
        return d
