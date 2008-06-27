"""
This module contains a series of classes that are used to model (in a very
simplified manner) services, groups of proxied hosts, and proxied hosts.

There are potentially many uses for such classes, but they are currently used
in order to separate configuration/application logic and the libraries. They do
this by mapping configuration information to model class instances.
"""


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


class ProxyGroup(object):
    """
    A class that represnts a group of hosts that need to be proxied.
    """
    def __init__(self, name, scheduler=None, enabled=False, hosts=[]):
        self.hosts = {}
        self.name = name
        self.isEnabled = enabled
        self.lbType = scheduler
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


    def getHosts(self):
        """
        Return the keys and values of the hosts attribute.
        """
        return self.hosts.items()


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

