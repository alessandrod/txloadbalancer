from zope.interface import implements

from twisted.application import service
from twisted.application import internet

from txlb import proxy
from txlb import schedulers

class ProxiedService(service.Service):
    """

    """

class LoadBalancedService(service.MultiService):
    """
    A load balanced service, when load balancing is turned off, should simply
    serve up the data itself.

    When load balancing is turned on, it needs to create proxies for remote
    hosts. Proxies need a scheduler and a director, so those need to be
    instantiated as well.
    """
    implements(service.IService)

    def __init__(self, lbType, tracker):
        """

        """
        # XXX this may not be necessary if we can pull the proxy service name
        # and the group name out of the proxy collection
        self.tracker = tracker
        service.MultiService.__init__(self)
        self.primaryName = 'primary'
        self.proxyCollection = service.MultiService()
        self.proxyCollection.setName('proxies')
        self.proxyCollection.setServiceParent(self)
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
        self.scheduler = schedulers.schedulerFactory(lbType, self.tracker)

    def proxiesFactory(self, pm):
        """

        """
        for serviceName, proxies in pm.getProxies():
            # a service can listen on multiple hosts/ports
            for proxy in proxies:
                name = self._stringifyHostPort(proxy.host, proxy.port)
                proxyService = internet.TCPServer(
                    proxy.port, proxy.factory, interface=proxy.host)
                proxyService.setName(name)
                proxyService.setServiceParent(self.proxyCollection)
        return self.proxyCollection

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
