import time

from pydirector import pdconf, pdlogging

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
        if not len(scheduler.hosts):
            # All servers are down! Go into a more aggressive mode for
            # checking.
            forceCheck = True
        for bh in badHosts.keys():
            when, what = badHosts[bh]
            pdlogging.log("re-adding %s automatically\n"%str(bh),
                    datestamp=1)
            name = scheduler.getHostNames()[bh]
            del badHosts[bh]
            scheduler.newHost(bh, name)

def checkConfigChanges():
    pass
