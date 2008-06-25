from zope.interface import implements

from twisted.application import service

from txlb.proxy import Proxy

class ProxiedService(service.Service):
    """

    """

class LoadBalancedService(service.Service):
    """
    A load balanced service, when load balancing is turned off, should simply
    serve up the data itself.

    When load balancing is turned on, it needs to create proxies for remote
    hosts. Proxies need a scheduler and a director, so those need to be
    instantiated as well.
    """
    implements(IService)

    def __init__(self, lbType):
        """

        """
        self.primaryName = 'primary'
        self.proxies = service.MultiService()
        self.proxies.setParentService(self)
        self.scheduler = None
        self.setScheduler(lbType)

    def _stringifyHostPort(self, host, port):
        """
        We'll want to do something else with the naming...
        """
        return "%s:%s" % (host, port)

    def setScheduler(self, lbType):
        """

        """
        self.scheduler = schedulers.schedulerFactory(lbType)

    def proxiesFactory(self, hosts, lbType):
        """

        """
        for host, port in hosts:
            # XXX need to figure out naming in order to have accurate lookup...
            # this is just a temporary solution
            name = self._stringifyHostPort(host, port)
            director = manager.ProxyManager(host, port)
            proxy = Proxy(name, host, port, scheduler, director)
            proxyService = internet.TCPServer(
                proxy.port, proxy.factory, interface=proxy.host)
            proxyService.setServiceParent(self.proxies)

    def setPrimaryService(self, tcpService):
        """

        """
        tcpService.setName(self.primaryName)
        tcpService.setServiceParent(self)

    def getProxyService(self, host, port):
        # XXX need to figure out naming in order to have accurate lookup...
        # this is just a temporary solution
        name = self._stringifyHostPort(host, port)
        return self.proxies.getNamedService(name)

class DynamicLoadBalancedService(LoadBalancedService):
    """

    """
