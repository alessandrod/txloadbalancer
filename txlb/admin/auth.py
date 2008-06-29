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
    A class for checking the credentials of a load-balancer user.
    """
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword,)


    def __init__(self, adminConfig):
        self.adminConfig = adminConfig


    def getUser(self, username):
        """
        An alias to the admin configuration object for getting user
        information.
        """
        return self.adminConfig.getUser(username)


    def unauth(self, msg):
        """
        A convenience method for returning a failure with message.
        """
        return defer.fail(error.UnauthorizedLogin(msg))

    def requestAvatarId(self, credentials):
        """
        The main credentials-checking logic.
        """
        username = credentials.username
        userConfig = self.getUser(username)
        if not userConfig:
            return self.unauth('Unknown user')
        if util.checkCryptPassword(credentials.password, userConfig.password):
            return defer.succeed(credentials.username)
        else:
            return self.unauth('User/password not correct')
