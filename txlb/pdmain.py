#
# Copyright (c) 2002-2004 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pdmain.py,v 1.11 2004/12/14 13:31:39 anthonybaxter Exp $
#

import sys
if sys.version_info < (2,2):
    class object: pass
import threading

from pydirector import pdconf
from pydirector import pdadmin
from pydirector import pdmanager
from pydirector import pdnetwork
from pydirector import pdschedulers

class PythonDirector(object):
    """
    The purpose of this class is to do the following:
     * start the admin web server, if needed
     * start the scheduling manager
     * start the load-balancer listeners for enabled groups
    """
    def __init__(self, config):
        self.listeners = {}
        self.schedulers = {}
        self.manager = None
        self.conf = pdconf.PDConfig(config)
        self.createManager()
        self.createListeners()

    def start(self, profile=0):
        if self.conf.admin is not None:
            pdadmin.start(adminconf=self.conf.admin, director=self)
        self.manager.start()
        try:
            if profile:
                import hotshot
                print "creating profiling log"
                prof = hotshot.Profile("pydir.prof")
                try:
                    prof.runcall(pdnetwork.mainloop)
                finally:
                    print "closing profile log"
                    prof.close()
            else:
                pdnetwork.mainloop(timeout=4)
        except KeyboardInterrupt:
            sys.exit(0)

    def createManager(self):
        manager = pdmanager.SchedulerManager(self)
        mt = threading.Thread(target=manager.mainloop)
        mt.setDaemon(1)
        self.manager = mt

    def createSchedulers(self, service):
        for group in service.getGroups():
            s = pdschedulers.createScheduler(group)
            self.schedulers[(service.name,group.name)] = s

    def getScheduler(self, serviceName, groupName):
        return self.schedulers[(serviceName,groupName)]

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
