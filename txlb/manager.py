import os
import time
from datetime import datetime

from twisted.protocols import amp
from twisted.internet import protocol

from txlb import util
from txlb import model
from txlb import proxy
from txlb import config
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



def checkBadHosts(configuration, director):
    """
    This function checks the director's hosts marked as "unavailable" and puts
    them back into use.
    """
    if not configuration.manager.hostCheckEnabled:
        return
    for name, service in director.getServices():
        # since all proxies for a service share a tracker,
        # we only need to check the first proxy.
        group = service.getEnabledGroup()
        tracker = director.getTracker(name, group.name)
        badHosts = tracker.badhosts
        for hostPort, timeAndError in badHosts.items():
            when, what = badHosts[hostPort]
            logging.log("re-adding %s automatically\n" % str(hostPort))
            hostname = tracker.getHostNames()[hostPort]
            del badHosts[hostPort]
            tracker.newHost(hostPort, hostname)



def checkConfigChanges(configFile, configuration, director):
    """
    This function replaces the current on-disk configuration with the
    adjustments that have been made in-memory (likely from the admin web UI). A
    backup of the original is made prior to replacement.

    Also, changes made on disc should have the ability to be re-read into
    memory. Obviously there are all sorts of issues at play, here: race
    conditions, differences and the need to merge, conflict resolution, etc.
    """
    if not configuration.manager.configCheckEnabled:
        return
    # disable the admin UI or at the very least, make it read-only
    director.setReadOnly()
    # compare in-memory config with on-disk config
    current = configuration.toXML()
    disk = config.Config(configFile).toXML()
    if current != disk:
        print "Configurations are different; backing up and saving to disk ..."
        # backup old file
        backupFile = "%s-%s" % (
            configFile, datetime.now().strftime('%Y%m%d%H%M%S'))
        os.rename(configFile, backupFile)
        # save configuration
        fh = open(configFile, 'w+')
        fh.write(current)
        fh.close()
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



class ProxyManager(object):
    """
    The purpose of this class is to start the load-balancer proxies for
    enabled groups.

    Note that this was formerly known as the Director, thus all the 'director'
    variable names.
    """


    def __init__(self, services=[]):
        self.services = {}
        if services:
            for service in services:
                self.addService(service)
        self.proxies = {}
        # XXX hopefully, the trackers attribute is temporary
        self.trackers = {}
        self._connections = {}
        self.isReadOnly = False


    def setReadOnly(self):
        """
        Set the proxy manager to read-only; this is intended to be read by
        other parts of the application (such as the admin interface) whenever
        whenever mutable state items are being manipulated. It doesn't lock
        anything, it simply provides something that can be read.
        """
        self.isReadOnly = True


    def setReadWrite(self):
        """
        Set the proxy to read-write.
        """
        self.isReadOnly = False


    def setServices(self, services):
        """
        This method is for use when it is necssary to set a collection of
        model.ProxyService objects at once.
        """
        self.services = services


    def getServices(self):
        """
        Return the keys and values of the services attribute.
        """
        return self.services.items()


    def getFirstService(self):
        """
        This is useful when load balancing a service via the API, something
        that one only does with a single service.
        """
        return self.getServices()[0]


    def addService(self, service):
        """
        This method adds a model.ProxyService instance to the proxy manager.
        """
        self.services[service.name] = service


    def getService(self, serviceName):
        """
        model.ProxyService instances can be retrieved from the proxy manager by
        a key look-up
        """
        return self.services[serviceName]


    def getGroups(self, serviceName):
        """
        Get the keys and values for the groups in a given service.
        """
        return self.getService(serviceName).getGroups()


    def getGroup(self, serviceName, groupName):
        """
        For a proxy service that has been addded to the proxy manager,
        model.ProxyGroup instances can be added to it.
        """
        return self.getService(serviceName).getGroup(groupName)



    def getHost(self, serviceName, groupName, hostName):
        """
        mode.ProxyHost instances can be added to the proxy manager, but they
        need to be associated with a proxy service and a proxy group.
        """
        return self.getGroup().getHost(hostName)


    def addTracker(self, serviceName, groupName, tracker):
        """
        The tracker is the object that is responsible for recording the status
        of connections, number of failuers, number of open connections, etc. A
        tracker that is added to the proxy manager needs to be associated with
        a proxy service and a proxy group.
        """
        self.trackers[(serviceName, groupName)] = tracker


    def getTracker(self, serviceName, groupName):
        """
        Trackers can be looked up by the keys that were used to add them: proxy
        service and proxy group names.
        """
        return self.trackers[(serviceName,groupName)]


    def getScheduler(self, serviceName, groupName):
        """
        The sceduler is the object responsible for determining which host will
        accpet the latest proxied request.
        """
        return self.getGroup(serviceName, groupName).scheduler


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
        Create a new Proxy and add it to the internal data structure. Note that
        this is not a proxy model, but rather the proxy.Proxy object itself.
        The parameters passed to Proxy will tell the load balancer on what
        interface and port to listen for in-coming traffic.
        """
        # proxies are associated with a specific tracker; trackers are
        # associated with a specific service; proxies are also associated with
        # a specific service, so there doesn't seem to be any need for an
        # explicit association between proxies and trackers. The proxy can
        # access the pm, which get get the tracker it needs.
        p = proxy.Proxy(serviceName, host, port, self)
        self.addProxy(serviceName, p)


    def updateProxy(self, serviceName, index, newProxy):
        """
        Sometimes (as in the case of changing the port on which the proxy is
        listening) we need to update the proxy. This method allows one to do
        this by specficically indentifying the proxy.
        """
        self.proxies[serviceName][index] = newProxy


    def getProxies(self):
        """
        Return the keys and values for the proxies attribute. The proxies
        attribute on the proxy manager stores a dictionay of proxy.Proxy
        instances.
        """
        return self.proxies.items()


    def getProxy(self, serviceName, index=None):
        """
        A Proxy instance can be retrieve by the service name and (since there
        can be more than one port listening per service) index.
        """
        proxies = self.proxies[serviceName]
        if index == None:
            return proxies
        return proxies[index]


    def addHost(self, serviceName, groupName, proxiedName, ip, weight=1):
        """
        This method updates not only the tracker data, but the models as well.
        """
        tracker = self.getTracker(serviceName=serviceName, groupName=groupName)
        # XXX does the tracker need to know about weights?
        tracker.newHost(name=proxiedName, ip=ip)
        # add modeling information
        host, port = util.splitHostPort(ip)
        proxiedHost = model.ProxyHost(proxiedName, host, port, weight)
        self.getGroup(serviceName, groupName).addHost(proxiedHost)


    def delHost(self, serviceName, groupName, proxiedName, ip):
        """
        This method updates not only the tracker data, but the models as well.
        """
        tracker = self.getTracker(serviceName=serviceName, groupName=groupName)
        tracker.delHost(name=proxiedName, ip=ip)
        # remove from modeling information, too
        self.getGroup(serviceName, groupName).delHost(proxiedName)


    def switchGroup(self, serviceName, oldGroupName, newGroupName):
        """
        This method needs to update the two affected proxy group models and 
        setup the new tracker.
        """
        oldGroup = self.getService(serviceName).getGroup(oldGroupName)
        oldGroup.disable()
        newGroup = self.getService(serviceName).getGroup(newGroupName)
        newGroup.enable()
        for proxy in self.getProxy(serviceName):
            proxy.setTracker(newGroupName)


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
    # check to see what got passed, in case we need to convert it
    if isinstance(services[0], model.HostMapper):
        services = model.convertMapperToModel(services)
    # create the manager
    pm = ProxyManager(services)
    for serviceName, service in pm.getServices():
        # set up the trackers for each group
        for groupName, group in pm.getGroups(serviceName):
            tracker = HostTracking(group)
            scheduler = schedulers.schedulerFactory(group.lbType, tracker)
            pm.addTracker(serviceName, groupName, tracker)
        # now let's setup actual proxies for the hosts in the enabled group
        group = service.getEnabledGroup()
        # XXX maybe won't need this next line
        #enabledTracker = pm.getTracker(service.name, group.name)
        for host, port in service.addresses:
            pm.createProxy(serviceName, host, port)
        # return proxy manager
    return pm



class HostTracking(object):
    """
    This class is responsible for tracking proxied host metadata (such as
    connection information and failure counts).

    Schedulers are responsible for selecting the next proxied host that will
    recieve the client request. Schedulers dependent upon their related
    trackers (instances of this class) for connection information.
    """


    def __init__(self, proxyGroup):
        self.group = proxyGroup
        self.hosts = []
        self.hostnames = {}
        self.badhosts = {}
        self.openconns = {}
        # the values in self.available indicate the number of connections that
        # are currently being attempted; a down host is not in available
        self.available = {}
        self.failed = {}
        self.totalconns = {}
        self.lastclose = {}
        # this next attribute gets set when a Scheduler is iniated; this class
        # needs the scheduler attribute for nextHost calls
        self.scheduler = None
        self.initializeGroupHosts()


    def initializeGroupHosts(self):
        for hostName, host in self.group.getHosts():
            self.newHost((host.hostname, host.port), hostName)


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
            if self.failed.has_key(ip):
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

