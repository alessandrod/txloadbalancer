import time

from twisted.protocols import amp
from twisted.internet import protocol

from txlb import util

from txlb import proxy
from txlb import logging
from txlb import schedulers



class Error(Exception):
    pass



class UnknownHostAndPortError(Exception):
    """
    An operation was attempted that needed both host and port values to be
    defined.
    """



class UnknowndServiceError(Error):
    """
    An operation was invalid due to the fact that no service has been defined.
    """



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
            logging.log("re-adding %s automatically\n" % str(hostPort))
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



class GetClientAddress(amp.Command):
    """


    Note: supplied by Apple.
    """
    arguments = [('host', amp.String()),
                 ('port', amp.Integer())]


    response = [('host', amp.String()),
                ('port', amp.Integer())]


    errors = {UnknownHostAndPortError: 'UNKNOWN_PORT'}



class ControlProtocol(amp.AMP):
    """

    Note: supplied by Apple.
    """
    def __init__(self, director):
        self.director = director


    def getClientAddress(self, host, port):
        host, port = self.director.getClientAddress(host, port)
        if (host, port) == (None, None):
            raise UnknownHostAndPortError()
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



class ProxyService(object):
    """
    A class that represents a collection of groups whose hosts need to be
    proxied.
    """
    def __init__(self, ports=[], groups={}):
        self.ports = ports
        self.groups =groups


    def getEnabledGroup(self):
        """
        There should only ever be one enabled group. This method returns it
        """
        groups = [x for x in self.groups if x.isEnabled]
        if groups:
            return groups[0]



class ProxyGroup(object):
    """
    A class that represnts a group of hosts that need to be proxied.
    """
    def __init__(self):
        self.hosts = {}
        self.isEnabled = False


    def enable(self):
        """
        This method is required to be called in order for a group to be
        enabled. Only an enabled group can generate connection proxies.
        """
        self.isEnabled = True


    def disable(self):
        """

        """
        self.isEnabled = False



class ProxyHost(object):
    """
    A class that represents a host that needs to be proxied.
    """
    def __init__(self, name='', ipOrHost='', port=None):
        self.name = name
        self.hostname = ipOrHost
        self.port = port


class ProxyManager(object):
    """
    The purpose of this class is to start the load-balancer proxies for
    enabled groups.

    Note that this was formerly known as the Director, thus all the 'director'
    variable names.
    """
    def __init__(self, services={}):
        self.services = services
        self.proxies = {}
        # XXX hopefully, the trackers attribute is temporary
        self.trackers = {}
        self._connections = {}
        # XXX need to get rid of this call once the rewrite is finished
        self.createListeners()
        self.isReadOnly = False

    def setReadOnly(self):
        """

        """
        self.isReadOnly = True

    def setReadWrite(self):
        """

        """
        self.isReadOnly = False

    def setServices(self, services):
        """
        This method is for use when it is necssary to set a collection of
        ProxyService objects at once.
        """
        self.services = services

    def getServices(self):
        """
        Return the service collection of proxies.
        """
        return self.services

    def addService(self, service):
        """

        """
        self.services[service.name] = service

    def getService(self, serviceName):
        """

        """
        return self.services[serviceName]

    def getGroups(self, serviceName):
        """
        Get the list of groups in a given service.
        """
        return self.getService(serviceName).groups

    def getGroup(self, serviceName, groupName):
        """

        """
        return self.getService(serviceName).getGroup(groupName)


    def getHost(self, serviceName, groupName, hostName):
        """

        """
        return self.getGroup().getHost(hostName)


    def addTracker(self, serviceName, groupName, tracker):
        """

        """
        self.trackers[(serviceName, groupName)] = tracker


    def getTracker(self, serviceName, groupName):
        """

        """
        return self.trackers[(serviceName,groupName)]


    def getScheduler(self, serviceName, groupName):
        """
        The sceduler is the object responsible for determining which host will
        accpet the latest proxied request.
        """
        return self.getGroup(serviceName, groupName).scheduler


    def createTrackers(self, service):
        if not self.services:
            raise UndefinedServiceError
        # XXX groups are configuration level metadata and should be handled at
        # the application level, not the library level; schedulers only need
        # the lb algorithm type passed to them in order to be created
        for groupConfig in service.getGroups():
            tracker = HostTracking(groupConfig)
            scheduler = schedulers.schedulerFactory(
                groupConfig.scheduler, tracker)
            self.trackers[(service.name, groupConfig.name)] = tracker


    def addProxy(self, serviceName, proxy):
        """
        Add an already-created instance of proxy.Proxy to the manager's proxy
        list.
        """
        if not self.proxies.has_key(serviceName):
            self.proxies[serviceName] = []
        self.proxies[serviceName].append(proxy)


    def createProxy(self, serviceName, host, port):
        """
        Create a new Proxy and add it to the internal data structure.
        """
        # proxies are associated with a specific tracker; trackers are
        # associated with a specific service; proxies are also associated with
        # a specific service, so there doesn't seem to be any need for an
        # explicit association between proxies and trackers. The proxy can
        # access the pm, which get get the tracker it needs.
        p = proxy.Proxy(serviceName, host, port, self)
        self.addProxy(serviceName, p)

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
        # XXX probably going to rewrite this one completely...
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
        # XXX this needs to be completely reworked
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


def proxyManagerFactory(services):
    """
    This factory is for simplifying the common task of creating a proxy manager
    with presets for many attributes and/or much data.
    """
    # create the manager
    pm = proxyManager(services)
    for service in pm.getServices():
        # set up the trackers for each group
        for group in pm.getGroups(service.name):
            tracker = HostingTracking(group)
            scheduler = schedulers.schedulerFactory(group.scheduler, tracker)
            pm.addTracker(service.name, group.name, tracker)
        # now let's setup actual proxies for the hosts in the enabled group
        for group in esrvice.getEnabledGroup():
            # XXX maybe won't need this next line
            enabledTracker = pm.getTracker(service.name, group.name)
            for host, port in service.x:
                pm.createProxy(service.name, host, port)
        # return proxy manager
    return pm


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
        self.openconns = {}
        # the values in self.available indicate the number of connections that
        # are currently being attempted
        self.available = {}
        self.failed = {}
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
        def sorter(attr):
            sorts = {}
            data = getattr(self, attr)
            hostPortCounts = data.items()
            hostPortCounts.sort()
            for hostPort, count in hostPortCounts:
                sorts['%s:%s' % hostPort] = count
            return sorts
        stats = {}
        # we don't present open connections for hosts that aren't available
        stats['openconns'] = sorter('available')
        stats['totals'] = sorter('totalconns')
        stats['failed'] = sorter('failed')
        stats['bad'] = self.badhosts
        return stats

    def showStats(self, verbose=1):
        stats = []
        stats.append("%d open connections" % len(self.openconns.keys()))
        hostPortCounts = self.available.items()
        hostPortCounts.sort()
        stats = stats + [str(x) for x in hostPortCounts]
        if verbose:
            openHosts = [x[1] for x in self.openconns.values()]
            openHosts.sort()
            stats = stats + [str(x) for x in openHosts]
        return "\n".join(stats)

    def getHost(self, senderFactory, client_addr=None):
        host = self.scheduler.nextHost(client_addr)
        if not host:
            return None
        cur = self.available.get(host)
        self.openconns[senderFactory] = (time.time(), host)
        self.available[host] += 1
        return host

    def getHostNames(self):
        return self.hostnames

    def doneHost(self, senderFactory):
        try:
            t, host = self.openconns[senderFactory]
        except KeyError:
            return
        del self.openconns[senderFactory]
        if self.available.get(host) is not None:
            self.available[host] -= 1
            self.totalconns[host] += 1
        self.lastclose[host] = time.time()

    def newHost(self, ip, name):
        if type(ip) is not type(()):
            ip = util.splitHostPort(ip)
        self.hosts.append(ip)
        self.hostnames[ip] = name
        # XXX why is this needed too?
        self.hostnames['%s:%d' % ip] = name
        self.available[ip] = 0
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
            del self.available[ip]
            del self.failed[ip]
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
            epochTime, hostPort = self.openconns[senderFactory]
        except KeyError:
            if doLog:
                msg = """Wow, Bender says "We're boned." No hosts available.\n"""
                logging.log(msg)
            return
        if not self.failed.has_key(hostPort):
            self.failed[hostPort] = 1
        else:
            self.failed[hostPort] += 1
        if hostPort in self.hosts:
            if doLog:
                logging.log("marking host %s down (%s)\n" % (
                    str(hostPort), reason.getErrorMessage()))
            self.hosts.remove(hostPort)
        if self.available.has_key(hostPort):
            del self.available[hostPort]
        # XXX I don't think we want to delete the previously gathered stats for
        # the hosts that go bad... I'll keep this code here (but commented out)
        # in case there's a good reason for it and I'm nost not thinking of it
        # right now
        #if self.totalconns.has_key(hostPort):
        #    del self.totalconns[hostPort]
        self.badhosts[hostPort] = (time.time(), reason)
        # make sure we also mark this session as done.
        self.doneHost(senderFactory)

