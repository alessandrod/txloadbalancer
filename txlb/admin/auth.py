"""
Classes that relate to user authentication for the load-balancer.
"""
from zope.interface import implements

from twisted.cred import error
from twisted.cred import portal
from twisted.cred import checkers
from twisted.cred import credentials
from twisted.internet import defer

from txlb import util

class LBAdminAuthChecker(object):
    """

    """
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword,)


    def __init__(self, adminConfig):
        self.adminConfig = adminConfig


    def getUser(self, username):
        """

        """
        return self.adminConfig.getUser(username)


    def unauth(self, msg):
        """

        """
        return defer.fail(error.UnauthorizedLogin(msg))

    def requestAvatarId(self, credentials):
        """

        """
        username = credentials.username
        crypted = util.generateCryptedPass(credentials.password)
        userConfig = self.getUser(username)
        if not userConfig:
            return self.unauth('Unknown user')
        if crypted == userConfig.password:
            return defer.succeed(credentials.username)
        else:
            return self.unauth('User/password not correct')
