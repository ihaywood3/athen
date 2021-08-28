import os

from zope.interface import implementer

from twisted.logger import Logger
from twisted.internet import defer
from twisted.python import failure
from twisted.cred import error, credentials, checkers
from twisted.cred.portal import IRealm
from twisted.web.resource import IResource

from athen.hub import db


@implementer(checkers.ICredentialsChecker)
class AccountsChecker:

    credentialInterfaces = (credentials.IUsernamePassword,)

    def _cbPasswordMatch(self, matched, username):
        if matched:
            return username
        else:
            return failure.Failure(error.UnauthorizedLogin())

    def requestAvatarId(self, c):
        credential = credentials.IUsernamePassword(c, None)
        if credential:
            u = db.get_user(credential.username)
            if u:
                return defer.maybeDeferred(
                    u.check_password, credential.password
                ).addCallback(self._cbPasswordMatch, credential.username)
            else:
                a = db.Account(credential.username)
                a.set_password(credential.password)
                db.set_user(credential.username, a)
                return defer.succeed(credential.username)
        else:
            return defer.succeed(checkers.ANONYMOUS)


@implementer(IRealm)
class AuthRealm:
    def __init__(self, resource_class):
        self.resource_class = resource_class

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IResource in interfaces:
            return (IResource, self.resource_class(avatarId), lambda: None)
        raise NotImplementedError()
