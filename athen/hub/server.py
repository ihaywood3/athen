from twisted.internet import reactor, endpoints
from twisted.internet.ssl import Certificate
from twisted.web.server import Site
from twisted.web.resource import Resource


class CertPage(Resource):
    isLeaf = True

    def render_GET(self, request):
        HTML = """
<html><body><pre>
getPeerCertificate %r %r
</pre></body></html>"""
        cert = Certificate.peerFromTransport(request.transport)
        return bytes(HTML % (type(cert), cert), "ascii")


resource = CertPage()
site = Site(resource)
e = endpoints.serverFromString(
    reactor, "ssl:8443:certKey=server.crt:privateKey=server.key"
)
e.listen(site)
reactor.run()
