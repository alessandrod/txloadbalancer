from zope.interface import implements

from twisted.application import service
from twisted.application import internet

from txlb import schedulers


class LoadBalancedService(service.MultiService):
    """
    A load balanced service, when load balancing is turned off, should simply
    serve up the data itself.

    When load balancing is turned on, it needs to create proxies for remote
    hosts. Proxies need a scheduler and a director, so those need to be
    instantiated as well.
    """
    implements(service.IService)


    def __init__(self):
        """
        Set up the service structure that the LoadBalancedService will need.
        """
        service.MultiService.__init__(self)
        self.primaryName = 'primary'
        self.proxyCollection = service.MultiService()
        self.proxyCollection.setName('proxies')
        self.proxyCollection.setServiceParent(self)
        # this gets set with setScheduler when the proxies are created
        self.scheduler = None


    def _stringifyHostPort(self, host, port):
        """
        We'll want to do something else with the naming...
        """
        return "%s:%s" % (host, port)

    def getProxyName(self, host, port, index):
        """
        A convenience function for getting the proxy name by host, port, and
        index.
        """
        return self._stringifyHostPort(host, port) + '-%s' % index


    def setScheduler(self, lbType, tracker):
        """
        A convenience method for creating the appropriate scheduler, given a
        load-balancing type and its tracker.
        """
        self.scheduler = schedulers.schedulerFactory(lbType, tracker)


    def proxiesFactory(self, pm):
        """
        Iterate through the models of proxy service, proxy service groups of
        hosts, and individual proxied hosts, creating TCP services as
        neccessary and naming them for future reference.
        """
        serviceName, service = pm.getFirstService()
        group = service.getEnabledGroup()
        tracker = pm.getTracker(serviceName, group.name)
        self.setScheduler(group.lbType, tracker)
        for serviceName, proxies in pm.getProxies():
            # a service can listen on multiple hosts/ports
            for index, proxy in enumerate(proxies):
                name = self.getProxyName(proxy.host, proxy.port, index)
                proxyService = internet.TCPServer(
                    proxy.port, proxy.factory, interface=proxy.host)
                proxyService.setServiceParent(self.proxyCollection)
        return self.proxyCollection


    def setPrimaryService(self, tcpService):
        """

        """
        tcpService.setName(self.primaryName)
        tcpService.setServiceParent(self)


    def getProxyService(self, host, port, index):
        # XXX need to figure out naming in order to have accurate lookup...
        # this is just a temporary solution
        name = self.getProxyName(host, port, index)
        return self.proxies.getNamedService(name)



class DynamicLoadBalancedService(LoadBalancedService):
    """
    XXX TBD
    """
