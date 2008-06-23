import time

from twisted.protocols import amp
from twisted.internet import reactor
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
    for listeners in director.listeners.values():
        # since all listeners for a service share a scheduler,
        # we only need to check the first listener.
        scheduler = listeners[0].scheduler
        badHosts = scheduler.badhosts
        for bh in badHosts.keys():
            when, what = badHosts[bh]
            logging.log("re-adding %s automatically\n"%str(bh),
                    datestamp=1)
            name = scheduler.getHostNames()[bh]
            del badHosts[bh]
            scheduler.newHost(bh, name)

def checkConfigChanges():
    pass


class UnknownPortError(Exception):
    pass



class GetClientAddress(amp.Command):
    arguments = [('host', amp.String()),
                 ('port', amp.Integer())]

    response = [('host', amp.String()),
                ('port', amp.Integer())]

    errors = {UnknownPortError: 'UNKNOWN_PORT'}


class ControlProtocol(amp.AMP):
    def __init__(self, director):
        self.director = director

    def getClientAddress(self, host, port):
        host, port = self.director.getClientAddress(host, port)
        if (host, port) == (None, None):
            raise UnknownPortError()

        return {'host': host, 'port': port}
    GetClientAddress.responder(getClientAddress)


class ControlFactory(protocol.ServerFactory):
    def __init__(self, director):
        self.director = director

    def buildProtocol(self, addr):
        return ControlProtocol(self.director)


class ProxyManager(object):
    """
    The purpose of this class is to start the load-balancer listeners for
    enabled groups.

    Note that this was formerly known as the Director, thus all the 'director'
    variable names.
    """
    def __init__(self, configFile):
        self.listeners = {}
        self.schedulers = {}
        self._connections = {}
        self.conf = config.Config(configFile)
        self.createListeners()

    def getScheduler(self, serviceName, groupName):
        return self.schedulers[(serviceName,groupName)]

    def createSchedulers(self, service):
        for group in service.getGroups():
            s = schedulers.createScheduler(group)
            self.schedulers[(service.name,group.name)] = s

    def createListeners(self):
        for service in self.conf.getServices():
            self.createSchedulers(service)
            eg = service.getEnabledGroup()
            scheduler = self.getScheduler(service.name, eg.name)
            # handle multiple listeners for a service
            self.listeners[service.name] = []
            for lobj in service.listen:
                l = proxy.Listener(service.name, util.splitHostPort(lobj),
                                   scheduler, self)
                self.listeners[service.name].append(l)

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
        for listener in self.listeners[serviceName]:
            listener.setScheduler(scheduler)

    def getClientAddress(self, host, port):
        """

        """
        return self._connections.get((host, port), (None, None))

    def setClientAddress(self, host, peer):
        """

        """
        self._connections[host] = peer
