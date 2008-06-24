import time

from twisted.protocols import amp
from twisted.internet import protocol

from txlb import util
from txlb import config
from txlb import proxy
from txlb import logging
from txlb import schedulers


def checkBadHosts(director):
    """
    This function checks the director's hosts marked as "unavailable" and puts
    them back into use.
    """
    for name, proxy in director.proxies.items():
        # since all proxies for a service share a scheduler,
        # we only need to check the first listener.
        scheduler = proxy[0].scheduler
        badHosts = scheduler.badhosts
        for bh in badHosts.keys():
            print "bad host: ", bh
            when, what = badHosts[bh]
            logging.log("re-adding %s automatically\n"%str(bh),
                    datestamp=1)
            hostname = scheduler.getHostNames()[bh]
            del badHosts[bh]
            scheduler.newHost(bh, hostname)


def checkConfigChanges():
    """
    This function replaces the current on-disk configuration with the
    adjustments that have been made in-memory (likely from the admin web UI). A
    backup of the original is made prior to replacement.

    Also, changes made on disc should have the ability to be re-read into
    memory. Obviously there are all sorts of issues at play, here: race
    conditions, differences and the need to merge, conflict resolution, etc.
    """
    # disable the admin UI or at the very least, make it read-only
    # compare load-time config with on-disk config
    # compare load-time config with in-memory config
    # save configuration(s)
    # re-enable admin UI


class UnknownPortError(Exception):
    """

    """


class GetClientAddress(amp.Command):
    """


    Note: supplied by Apple.
    """
    arguments = [('host', amp.String()),
                 ('port', amp.Integer())]

    response = [('host', amp.String()),
                ('port', amp.Integer())]

    errors = {UnknownPortError: 'UNKNOWN_PORT'}


class ControlProtocol(amp.AMP):
    """

    Note: supplied by Apple.
    """
    def __init__(self, director):
        self.director = director

    def getClientAddress(self, host, port):
        host, port = self.director.getClientAddress(host, port)
        if (host, port) == (None, None):
            raise UnknownPortError()

        return {'host': host, 'port': port}
    GetClientAddress.responder(getClientAddress)


class ControlFactory(protocol.ServerFactory):
    """

    Note: supplied by Apple.
    """
    def __init__(self, director):
        self.director = director

    def buildProtocol(self, addr):
        return ControlProtocol(self.director)


class ProxyManager(object):
    """
    The purpose of this class is to start the load-balancer proxies for
    enabled groups.

    Note that this was formerly known as the Director, thus all the 'director'
    variable names.
    """
    def __init__(self, configFile):
        self.proxies = {}
        self.schedulers = {}
        self._connections = {}
        self.conf = config.Config(configFile)
        self.createListeners()
        self.proxyCollection = None

    def setServices(self, serviceCollection):
        """
        This method is for use when a collection of Twisted services has been
        created, contining named services (actually TCP servers) that map to
        the proxy.Proxy instances tracked in ProxyManager.proxies.
        """
        self.proxyCollection = serviceCollection

    def getServices(self):
        """
        Return the service collection of proxies.
        """
        return self.proxyCollection

    def getScheduler(self, serviceName, groupName):
        return self.schedulers[(serviceName,groupName)]

    def createSchedulers(self, service):
        for group in service.getGroups():
            s = schedulers.schedulerFactory(group)
            self.schedulers[(service.name,group.name)] = s

    def createListeners(self):
        for service in self.conf.getServices():
            self.createSchedulers(service)
            eg = service.getEnabledGroup()
            scheduler = self.getScheduler(service.name, eg.name)
            # if we ever need to support multiple proxies per service, this
            # will need to be changed
            self.proxies[service.name] = []
            for lobj in service.listen:
                host, port = util.splitHostPort(lobj)
                l = proxy.Proxy(service.name, host, port, scheduler, self)
                self.proxies[service.name].append(l)

    def enableGroup(self, serviceName, groupName):
        serviceConf = self.conf.getService(serviceName)
        group = serviceConf.getGroup(groupName)
        if group:
            serviceConf.enabledgroup = groupName
        self.switchScheduler(serviceName)

    def switchScheduler(self, serviceName):
        """
        switch the scheduler for a listener. this is needed, e.g. if
        we change the active group
        """
        serviceConf = self.conf.getService(serviceName)
        eg = serviceConf.getEnabledGroup()
        scheduler = self.getScheduler(serviceName, eg.name)
        for listener in self.proxies[serviceName]:
            listener.setScheduler(scheduler)

    def getClientAddress(self, host, port):
        """

        """
        return self._connections.get((host, port), (None, None))

    def setClientAddress(self, host, peer):
        """

        """
        self._connections[host] = peer

