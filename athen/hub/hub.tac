from twisted.application import internet, service
from twisted.cred.checkers import ANONYMOUS
from twisted.web import server
from twisted.web.resource import Resource
from twisted.cred.portal import Portal
from twisted.web.guard import BasicCredentialFactory, HTTPAuthSessionWrapper

from athen.hub import resource, auth


def getWebService():
    portal = Portal(auth.AuthRealm(resource.FHIRPage), [auth.AccountsChecker()])
    root = Resource()
    root.putChild(
        b"auth",
        HTTPAuthSessionWrapper(
            portal, [BasicCredentialFactory("athen FHIR REST server")]
        ),
    )
    root.putChild(b"public", resource.FHIRPage(ANONYMOUS))
    site = server.Site(root)
    return internet.TCPServer(8080, site)


application = service.Application("athen hub")

# attach the service to its parent application
_service = getWebService()
_service.setServiceParent(application)
