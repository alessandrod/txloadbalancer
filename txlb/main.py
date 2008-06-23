from twisted.protocols import amp
from twisted.internet import reactor
from twisted.internet import protocol

from txlb import conf
from txlb import loaders
from txlb import schedulers


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
        return PDControlProtocol(self.director)


class Director(object):
    """
    The purpose of this class is to start the load-balancer listeners for
    enabled groups.
    """
    def __init__(self, config):
        self.listeners = {}
        self.schedulers = {}
        self._connections = {}
        self.conf = conf.Config(config)
        self.createListeners()
        if hasattr(self.conf, "socket"):
            reactor.listenUNIX(self.conf.socket, ControlFactory(self))

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
                l = loaders.Listener(service.name,
                                   conf.splitHostPort(lobj),
                                   scheduler)
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
