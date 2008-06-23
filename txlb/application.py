from twisted.web import server
from twisted.internet import ssl
from twisted.application import service
from twisted.application import internet
from twisted.application import strports

from txlb import name
from txlb import util
from txlb import manager
from txlb.admin import pages
from txlb.manager import checkBadHosts


def setup(configFile):
    """
    Given the configuration file, instantiate the proxy manager and setup the
    necessary services.
    """
    application = service.Application(name)
    services = service.IServiceCollection(application)

    # set up the director
    director = manager.ProxyManager(configFile)

    # set up the web server
    site = server.Site(pages.AdminServer(director))
    adminPort = director.conf.admin.listen[1]
    if director.conf.admin.secure:
        util.setupServerCert()
        context = ssl.DefaultOpenSSLContextFactory(util.privKeyFile, util.certFile)
        admin = internet.SSLServer(adminPort, site, context)
    else:
        admin = internet.TCPServer(adminPort, site)
    admin.setServiceParent(services)

    # set up the manager timer service
    checkInterval = director.conf.manager.hostCheckInterval
    checker = internet.TimerService(checkInterval, checkBadHosts, director)
    checker.setServiceParent(services)

    return application
