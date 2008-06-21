from pydirector import pdconf
from pydirector import pdnetwork
from pydirector import pdschedulers

class Director(object):
    """
    The purpose of this class is to start the load-balancer listeners for
    enabled groups.
    """
    def __init__(self, config):
        self.listeners = {}
        self.schedulers = {}
        self.conf = pdconf.PDConfig(config)
        self.createListeners()

    def getScheduler(self, serviceName, groupName):
        return self.schedulers[(serviceName,groupName)]

    def createSchedulers(self, service):
        for group in service.getGroups():
            s = pdschedulers.createScheduler(group)
            self.schedulers[(service.name,group.name)] = s

    def createListeners(self):
        for service in self.conf.getServices():
            self.createSchedulers(service)
            eg = service.getEnabledGroup()
            scheduler = self.getScheduler(service.name, eg.name)
            # handle multiple listeners for a service
            self.listeners[service.name] = []
            for lobj in service.listen:
                l = pdnetwork.Listener(service.name,
                                   pdconf.splitHostPort(lobj),
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
