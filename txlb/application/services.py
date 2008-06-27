from twisted.web import server
from twisted.internet import ssl
from twisted.application import service
from twisted.application import internet

from txlb import name
from txlb import util
from txlb import model
from txlb import config
from txlb import manager
from txlb.admin import pages
from txlb.manager import checkBadHosts



def configuredProxyManagerFactory(configuration):
    """
    A factory for generating a ProxyManager, complete with pre-created
    services, groups, and data from a configuration file. Most of the work here
    is mapping configuration to models. The collection of models is what is
    passed to the proxyManagerFactory.
    """
    services = []
    # build services from configuration
    for serviceName, serviceConf in configuration.services.items():
        addresses = [util.splitHostPort(x) for x in serviceConf.listen]
        pservice = model.ProxyService(serviceName, addresses=addresses)
        # build groups
        for groupName, groupConf in serviceConf.groups.items():
            # build hosts
            # XXX ugh; some of the configuration XML is braindead
            enabled = False
            if groupConf == serviceConf.getEnabledGroup():
                enabled = True
            pgroup = model.ProxyGroup(groupName, groupConf.scheduler, enabled)
            for hostName, hostConf in groupConf.hosts.items():
                host, port = util.splitHostPort(hostConf.ip)
                phost = model.ProxyHost(hostName, host, port)
                # add the host to the group
                pgroup.addHost(phost)
            # add the group to the service
            pservice.addGroup(pgroup)
        # add the service to the service collection
        services.append(pservice)
    # call the proxyManagerFactory and return it
    return manager.proxyManagerFactory(services)



def setupAdminServer(configuration, director):
    """
    Given the director, set up a potentially SSL-enabled admin web UI on the
    configured port.
    """
    root = pages.AdminServer(configuration, director)
    site = server.Site(root)
    adminPort = int(configuration.admin.listen[1])
    if configuration.admin.secure:
        util.setupServerCert()
        context = ssl.DefaultOpenSSLContextFactory(
            util.privKeyFile, util.certFile)
        admin = internet.SSLServer(adminPort, site, context)
    else:
        admin = internet.TCPServer(adminPort, site)
    admin.setName('admin')
    return admin



def setupHostChecker(configuration, director):
    """
    This is the setup for the "bad host check" management task.
    """
    checkInterval = configuration.manager.hostCheckInterval
    checker = internet.TimerService(checkInterval, checkBadHosts, director)
    checker.setName('hostChecker')
    return checker



def setupControlSocket(configuration, director):
    """
    This is for the functionaity that Apple introduced in the patches from its
    Calendar Server project.
    """
    control = service.Service()
    socket = configuration.socket
    if socket != None:
        control = internet.UNIXServer(socket, manager.ControlFactory(director))
    control.setName('control')
    return control



def setupProxyServices(director):
    """
    Set up proxies for each service the proxy manager balances. Additionally,
    the director gets a reference to the proxies.
    """
    proxyCollection = service.MultiService()
    proxyCollection.setName('proxies')
    for serviceName, proxies in director.getProxies():
        # a service can listen on multiple hosts/ports
        for proxy in proxies:
            proxyService = internet.TCPServer(
                proxy.port, proxy.factory, interface=proxy.host)
            proxyService.setName("%s %s:%s" % (
                serviceName, proxy.host, proxy.port))
            proxyService.setServiceParent(proxyCollection)
    return proxyCollection



def setup(configFile):
    """
    Given the configuration file, instantiate the proxy manager and setup the
    necessary services.
    """
    # get config object
    conf = config.Config(configFile)

    application = service.Application(name)
    services = service.IServiceCollection(application)

    # instantiate the proxy manager (that which will direct the proxies)
    director = configuredProxyManagerFactory(conf)

    # set up the proxies
    proxies = setupProxyServices(director)
    proxies.setServiceParent(services)

    # set up the control socket
    control = setupControlSocket(conf, director)
    control.setServiceParent(services)

    # set up the web server
    admin = setupAdminServer(conf, director)
    admin.setServiceParent(services)

    # set up the host checker service
    checker = setupHostChecker(conf, director)
    checker.setServiceParent(services)

    # return the application object so that the .tac file can use it
    return application


