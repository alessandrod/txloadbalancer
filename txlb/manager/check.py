import os
from datetime import datetime

from txlb import config
from txlb import logging



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
