"""
This module contains a series of classes that are used to model (in a very
simplified manner) services, groups of proxied hosts, and proxied hosts.

There are potentially many uses for such classes, but they are currently used
in order to separate configuration/application logic and the libraries. They do
this by mapping configuration information to model class instances.
"""
from txlb import util


class HostMapper(object):
    """
    This is a peace-of-mind convenience class for developers that use the
    load-balancing API, providing a quick and intuitive means of configuring a
    load-balancing service without a config file or lots of structured data.

    @type proxy: string
    @param proxy: the name that the proxy service will be known by

    @type addresses: string or list
    @param addresses: a string or list of strings of the form 'host:port'

    @type group: string
    @param group: the group that the host will be put into

    @type address: string
    @param address: a string of the form 'host:port' that is being
                    load-balanced by the proxy service

    @type enabled: boolean or None
    @param enabled: a boolean that indicates whether the group for the host is
                    to be enabled, disabled, or ignored (None)
    """
    def __init__(self, proxy='', addresses=[], group='', lbType='', host='', address='',
                 enabled=None, weight=1):
        if isinstance(addresses, str):
            addresses = [addresses]
        self.proxyName = proxy
        self.proxyAddresses = [util.splitHostPort(x) for x in addresses]
        self.groupName = group
        self.lbType = lbType
        self.hostName = host
        self.hostAddress = util.splitHostPort(address)
        self.groupEnabled = enabled
        self.hostWeight = weight



def convertMapperToModel(listOfMappers):
    """
    This is the method that does the actual conversion from simple mapper
    data structure to an appropriate collection of models.
    """
    # create some dictionaries that will be used to ensure non-duplication of
    # services and service groups
    proxyHolder = {}
    groupHolder = {}
    for mapper in listOfMappers:
        service = ProxyService(mapper.proxyName, mapper.proxyAddresses)
        service = proxyHolder.setdefault(mapper.proxyName, service)
        group = ProxyGroup(
            mapper.groupName, mapper.lbType, mapper.groupEnabled)
        group = groupHolder.setdefault(mapper.groupName, group)
        host = ProxyHost(
            mapper.hostName, mapper.hostAddress[0], mapper.hostAddress[1],
            mapper.hostWeight)
        group.addHost(host)
        service.addGroup(group)
    # we only need the list of proxies, so we just return the values of the
    # dict
    return proxyHolder.values()

class ProxyService(object):
    """
    A class that represents a collection of groups whose hosts need to be
    proxied.
    """
    def __init__(self, name, addresses=[], groups=[]):
        self.groups = {}
        self.name = name
        self.addresses = addresses
        if groups:
            for group in groups:
                self.addGroup(group)


    def getEnabledGroup(self):
        """
        There should only ever be one enabled group. This method returns it. If
        there is more than one enabled group, only the first one this method
        finds will be returned.
        """
        groups = [x for x in self.groups.values() if x.isEnabled]
        if groups:
            return groups[0]


    def addGroup(self, proxyGroup):
        """
        Update the service's group data structure with a new ProxyGroup
        instance.
        """
        self.groups[proxyGroup.name] = proxyGroup


    def getGroups(self):
        """
        Return the keys and values of the groups attribute.
        """
        return self.groups.items()


    def getGroup(self, groupName):
        """
        Return the group with the given name.
        """
        return self.groups[groupName]


class ProxyGroup(object):
    """
    A class that represnts a group of hosts that need to be proxied.
    """
    def __init__(self, name, scheduler=None, enabled=False, hosts=[]):
        self.hosts = {}
        self.name = name
        self.isEnabled = enabled
        self.lbType = scheduler
        self.weights = {}
        if hosts:
            for host in hosts:
                self.addHost(host)


    def enable(self):
        """
        This method is required to be called in order for a group to be
        enabled. Only an enabled group can generate connection proxies.
        """
        self.isEnabled = True


    def disable(self):
        """
        This method needs to be called in order to disable a group. If it is
        not called, and there are two enabled groups, only one group will be
        retuted by ProxyService.getEneabledGroup.
        """
        self.isEnabled = False


    def addHost(self, proxyHost):
        """
        Update the group's hosts data structure with a new ProxyHost instance.
        """
        self.hosts[proxyHost.name] = proxyHost
        self.weights[(proxyHost.hostname, proxyHost.port)] = proxyHost.weight


    def getHosts(self):
        """
        Return the keys and values of the hosts attribute.
        """
        return self.hosts.items()

    def getHost(self, name):
        """
        A convenience method for getting a host proxy from the group proxy,
        given the ProxyHost name.
        """
        return self.hosts[name]


    def delHost(self, name):
        """
        Remove the host from the group model.
        """
        del self.hosts[name]


    def getHostByHostame(self, hostname):
        """
        A convenience method for getting a host proxy from the group proxy,
        given its hostname.
        """
        host, port = util.splitHostPort(hostname)
        for host in self.hosts.values():
            if host.hostname == host and host.port == port:
                return host


    def getHostWeight(self, hostPort):
        """
        Get the weighted value for a given host proxy, given either the host
        proxy's name or hostname.
        """
        return self.weights[hostPort]


    def getWeights(self):
        """
        Get all the weights associated with this host proxies for this group.
        """
        return self.weights


    def getWeightDistribution(self, hostPorts=[]):
        """
        Build a sample population of host, one per weight value (e.g., a host
        with a weight of 1 will have one entry in the distribution; one with a
        weight of 5 will have 5 entries in the distribution). Optionally,
        filter by (host, port) tuples, including only those hosts that are that
        are passed in hostnames filter keyword argument.
        """
        weights = self.getWeights().items()
        if hostPorts:
            weights = [(x, y) for x, y in weights if x in hostPorts]
        for hostPort, weight in weights:
            for x in xrange(weight):
                yield hostPort



class ProxyHost(object):
    """
    A class that represents a host that needs to be proxied.
    """
    def __init__(self, name='', ipOrHost='', port=0, weight=1):
        self.name = name
        self.hostname = ipOrHost
        self.port = int(port)
        self.weight = weight
        self.fileTypes = []
        self.protocols = []


    def setWeight(self, weight):
        """
        This method is useful when the weighting for a host needs to be changed
        programmatically while a service is actively being load-balanced.
        """
        self.weight = weight


    def setAcceptedFileTypes(self, fileTypes=[]):
        """
        This sets the list of file types that the proxied host should accept.

        An empty list means "accept all."
        """
        self.fileTypes = fileTypes


    def setAcceptedProtcols(self, protocols=[]):
        """
        This sets the protocols (e.g., schema, for HTTP requests) that the
        proxied host should accept.

        An empty list means "accept all."
        """
        self.protocols = protocols

