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
        # since all proxies for a service share a tracker,
        # we only need to check the first proxy.
        tracker = proxy[0].tracker
        badHosts = tracker.badhosts
        for hostPort, timeAndError in badHosts.items():
            when, what = badHosts[hostPort]
            logging.log("re-adding %s automatically\n" % str(hostPort),
                    datestamp=1)
            hostname = tracker.getHostNames()[hostPort]
            del badHosts[hostPort]
            tracker.newHost(hostPort, hostname)


def checkConfigChanges(director):
    """
    This function replaces the current on-disk configuration with the
    adjustments that have been made in-memory (likely from the admin web UI). A
    backup of the original is made prior to replacement.

    Also, changes made on disc should have the ability to be re-read into
    memory. Obviously there are all sorts of issues at play, here: race
    conditions, differences and the need to merge, conflict resolution, etc.
    """
    # disable the admin UI or at the very least, make it read-only
    director.setReadOnly()
    # compare load-time config with on-disk config
    # compare load-time config with in-memory config
    # save configuration(s)
    # re-enable admin UI
    director.setReadWrite()


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
        # XXX hopefully, the trackers attribute is temporary
        self.trackers = {}
        self._connections = {}
        self.conf = config.Config(configFile)
        self.createListeners()
        self.proxyCollection = None
        self.isReadOnly = False

    def setReadOnly(self):
        """

        """
        self.isReadOnly = True

    def setReadWrite(self):
        """

        """
        self.isReadOnly = False

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

    def getTracker(self, serviceName, groupName):
        return self.trackers[(serviceName,groupName)]

    def getScheduler(self, serviceName, groupName):
        return self.getTracker(serviceName, groupName).scheduler

    def createTrackers(self, service):
        # XXX groups are configuration level metadata and should be handled at
        # the application level, not the library level; schedulers only need
        # the lb algorithm type passed to them in order to be created
        for groupConfig in service.getGroups():
            tracker = HostTracking(groupConfig)
            scheduler = schedulers.schedulerFactory(
                groupConfig.scheduler, tracker)
            self.trackers[(service.name, groupConfig.name)] = tracker

    def createListeners(self):
        for service in self.conf.getServices():
            self.createTrackers(service)
            eg = service.getEnabledGroup()
            tracker = self.getTracker(service.name, eg.name)
            self.proxies[service.name] = []
            for lobj in service.listen:
                host, port = util.splitHostPort(lobj)
                l = proxy.Proxy(service.name, host, port, tracker, self)
                self.proxies[service.name].append(l)

    def enableGroup(self, serviceName, groupName):
        serviceConf = self.conf.getService(serviceName)
        group = serviceConf.getGroup(groupName)
        if group:
            serviceConf.enabledgroup = groupName
        self.switchTracker(serviceName)

    def switchTracker(self, serviceName):
        """
        switch the tracker for a proxy. this is needed, e.g. if we change the
        active group
        """
        serviceConf = self.conf.getService(serviceName)
        eg = serviceConf.getEnabledGroup()
        tracker = self.getTracker(serviceName, eg.name)
        for proxy in self.proxies[serviceName]:
            proxy.setTracker(tracker)

    def getClientAddress(self, host, port):
        """

        """
        return self._connections.get((host, port), (None, None))

    def setClientAddress(self, host, peer):
        """

        """
        self._connections[host] = peer


class HostTracking(object):
    """
    Schedulers are responsible for selecting the next proxied host that will
    recieve the client request.
    """
    # XXX passing a configuration object is uncool and application-level; we
    # should only pass what is necessary here, and let configuration happen
    # higher up; it might be appropriate, however, to have objeects that model
    # services, groups, and hosts with information from the configuration file
    # stored in these model isntances; passing a model instance would be fine,
    # if it's absolutely necessary
    def __init__(self, groupConfig):
        self.hosts = []
        self.hostnames = {}
        self.badhosts = {}
        self.open = {}
        self.openconns = {}
        self.totalconns = {}
        self.lastclose = {}
        self.loadConfig(groupConfig)
        # this next attribute gets set when a Scheduler is iniated; this class
        # needs the scheduler attribute for nextHost calls
        self.scheduler = None

    def loadConfig(self, groupConfig):
        self.group = groupConfig
        hosts = self.group.getHosts()
        for host in hosts:
            self.newHost(host.ip, host.name)

    def getStats(self):
        stats = {}
        stats['open'] = {}
        stats['totals'] = {}
        hostPortCounts = self.openconns.items()
        hostPortCounts.sort()
        for hostPort, count in hostPortCounts:
            stats['open']['%s:%s' % hostPort] = count
        hostPortCount = self.totalconns.items()
        hostPortCount.sort()
        for hostPort, count in hostPortCount:
            stats['totals']['%s:%s' % hostPort] = count
        badHosts = self.badhosts
        stats['bad'] = badHosts
        return stats

    def showStats(self, verbose=1):
        stats = []
        stats.append( "%d open connections" % len(self.open.keys()) )
        hostPortCounts = self.openconns.items()
        hostPortCounts.sort()
        stats = stats + [str(x) for x in hostPortCounts]
        if verbose:
            openHosts = [x[1] for x in self.open.values()]
            openHosts.sort()
            stats = stats + [str(x) for x in openHosts]
        return "\n".join(stats)

    def getHost(self, senderFactory, client_addr=None):
        host = self.scheduler.nextHost(client_addr)
        if not host:
            return None
        cur = self.openconns.get(host)
        self.open[senderFactory] = (time.time(), host)
        self.openconns[host] += 1
        return host

    def getHostNames(self):
        return self.hostnames

    def doneHost(self, senderFactory):
        try:
            t, host = self.open[senderFactory]
        except KeyError:
            return
        del self.open[senderFactory]
        if self.openconns.get(host) is not None:
            self.openconns[host] -= 1
            self.totalconns[host] += 1
        self.lastclose[host] = time.time()

    def newHost(self, ip, name):
        if type(ip) is not type(()):
            ip = util.splitHostPort(ip)
        self.hosts.append(ip)
        self.hostnames[ip] = name
        # XXX why is this needed too?
        self.hostnames['%s:%d' % ip] = name
        self.openconns[ip] = 0
        self.totalconns[ip] = 0

    def delHost(self, ip=None, name=None, activegroup=0):
        """
        remove a host
        """
        if ip is not None:
            if type(ip) is not type(()):
                ip = util.splitHostPort(ip)
        elif name is not None:
            for ip in self.hostnames.keys():
                if self.hostnames[ip] == name:
                    break
            raise ValueError, "No host named %s"%(name)
        else:
            raise ValueError, "Neither ip nor name supplied"
        if activegroup and len(self.hosts) == 1:
            return 0
        if ip in self.hosts:
            self.hosts.remove(ip)
            del self.hostnames[ip]
            del self.openconns[ip]
            del self.totalconns[ip]
        elif self.badhosts.has_key(ip):
            del self.badhosts[ip]
        else:
            raise ValueError, "Couldn't find host"
        return 1

    def deadHost(self, senderFactory, reason='', doLog=True):
        """
        This method gets called when a proxied host is unreachable.
        """
        # if this throws an exception here, I think it's because all the hosts
        # have been removed from the pool
        try:
            epochTime, hostPort = self.open[senderFactory]
        except KeyError:
            if doLog:
                msg = """Wow, Bender says "We're boned." No hosts available.\n"""
                logging.log(msg)
            return
        if hostPort in self.hosts:
            if doLog:
                logging.log("marking host %s down (%s)\n" % (
                    str(hostPort), reason.getErrorMessage()))
            self.hosts.remove(hostPort)
        if self.openconns.has_key(hostPort):
            del self.openconns[hostPort]
        # XXX I don't think we want to delete the previously gathered stats for
        # the hosts that go bad... I'll keep this code here (but commented out)
        # in case there's a good reason for it and I'm nost not thinking of it
        # right now
        #if self.totalconns.has_key(hostPort):
        #    del self.totalconns[hostPort]
        self.badhosts[hostPort] = (time.time(), reason)
        # make sure we also mark this session as done.
        self.doneHost(senderFactory)

