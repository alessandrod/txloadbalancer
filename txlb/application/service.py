from zope.interface import implements

from twisted.internet import defer
from twisted.application import service
from twisted.application import internet

from txlb import proxy
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


    def __init__(self, pm):
        """
        Set up the service structure that the LoadBalancedService will need.
        """
        service.MultiService.__init__(self)
        self.director = pm
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


    def getProxyName(self, name, index):
        """
        A convenience function for getting the proxy name by host, port, and
        index.
        """
        return '%s-%s' % (name, index)


    def getServiceName(self, proxyName):
        """
        A convenience function for getting the service name back from a proxy
        name.
        """
        parts = proxyName.split('-')
        if len(parts) <= 1:
            return (proxyName, None)
        index = int(parts[-1])
        return ('-'.join(parts[:-1]), index)


    def setScheduler(self, lbType, tracker):
        """
        A convenience method for creating the appropriate scheduler, given a
        load-balancing type and its tracker.
        """
        self.scheduler = schedulers.schedulerFactory(lbType, tracker)


    def proxyFactory(self, name, port, factory, interface):
        """
        A factory for creating proxy servers.
        """
        # update the proxy manager's proxy instance
        proxyService = internet.TCPServer(port, factory, interface=interface)
        proxyService.setName(name)
        proxyService.setServiceParent(self.proxyCollection)
        return proxyService


    def proxiesFactory(self):
        """
        Iterate through the models of proxy service, proxy service groups of
        hosts, and individual proxied hosts, creating TCP services as
        neccessary and naming them for future reference.
        """
        serviceName, service = self.director.getFirstService()
        group = service.getEnabledGroup()
        tracker = self.director.getTracker(serviceName, group.name)
        self.setScheduler(group.lbType, tracker)
        for serviceName, proxies in self.director.getProxies():
            # a service can listen on multiple hosts/ports
            for index, proxy in enumerate(proxies):
                # if there's only one port that this proxy service will be
                # listening on, there's not need to give it an indexed name
                name = serviceName
                if len(proxies) > 1:
                    index += 1
                    name = self.getProxyName(serviceName, index)
                self.proxyFactory(name, proxy.port, proxy.factory, proxy.host)
        return self.proxyCollection


    def setPrimaryService(self, tcpService):
        """

        """
        # XXX this isn't used right now and *might* not be needed...
        tcpService.setName(self.primaryName)
        tcpService.setServiceParent(self)


    def getProxyService(self, serviceName, index=None):
        # XXX need to figure out naming in order to have accurate lookup...
        # this is just a temporary solution
        if index:
            serviceName = self.getProxyName(serviceName, index)
        return self.proxyCollection.getServiceNamed(serviceName)


    def getProxyNames(self):
        """
        A convenience method for getting a list of names used in the proxies
        collection of named services.
        """
        return self.proxyCollection.namedServices.keys()


    def switchPort(self, proxyName, newPort):
        """
        The best way to print up a proxy on a new port is to down the old one
        and create a new one on the desired port.
        """
        oldService = self.getProxyService(proxyName)
        oldService.disownServiceParent()
        serviceName, index = self.getServiceName(proxyName)
        if index == None:
            index = 0
        else:
            index -= 1
        oldProxy = self.director.getProxy(serviceName, index)
        newProxy = proxy.Proxy(
            serviceName, oldProxy.host, newPort, self.director)
        newService = self.proxyFactory(
            proxyName, newPort, newProxy.factory, newProxy.host)
        newService.startService()
        self.director.updateProxy(serviceName, index, newProxy)



class DynamicLoadBalancedService(LoadBalancedService):
    """
    XXX TBD
    """
