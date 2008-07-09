import os
from datetime import datetime

from twisted.python import log
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import protocol

from txlb import config
from txlb import logging



class PingProtocol(protocol.Protocol):
    """
    A simple protocol for doing nothing other than making a connection. Used in
    TCP pinging.
    """
    def connectionMade(self):
        self.factory.deferred.callback("success")
        self.factory.incrementCount()
        self.transport.loseConnection()



class PingFactory(protocol.ClientFactory):
    """
    The factory used when creating a "pinger."
    """
    protocol = PingProtocol


    def __init__(self):
        self.deferred = defer.Deferred()
        self.count = 0


    def clientConnectionFailed(self, connector, reason):
        self.deferred.errback(reason)


    def clientConnectionLost(self, connector, reason):
        pass


    def incrementCount(self):
        self.count += 1



def ping(host, port, tries=4, timeout=5):
    """

    """
    deferreds = []
    for i in xrange(tries):
        factory = PingFactory()
        reactor.connectTCP(host, port, factory, timeout=timeout)
        deferreds.append(factory.deferred)
    return defer.DeferredList(deferreds, consumeErrors=1)



def checkBadHosts(configuration, director):
    """
    This function checks the director's hosts marked as "unavailable" and puts
    them back into use.
    """
    def _makeGood(result, tracker, hostPort):
        # remember that the result is from a deferred list, so it's a a list of
        # (Bool, result/failure) tuples; if there are any problems at all
        # connecting to the host, we don't want to put it back into rotation
        if False in [x[0] for x in result]:
            logging.log("Host %s is still down.\n" % str(hostPort))
            return
        logging.log("Host is back up; re-adding %s ...\n" % str(hostPort))
        del tracker.badhosts[hostPort]
        hostname = tracker.getHostNames()[hostPort]
        tracker.newHost(hostPort, hostname)

    if not configuration.manager.hostCheckEnabled:
        return
    for name, service in director.getServices():
        # since all proxies for a service share a tracker,
        # we only need to check the first proxy.
        group = service.getEnabledGroup()
        tracker = director.getTracker(name, group.name)
        badHosts = tracker.badhosts
        for hostPort, timeAndError in badHosts.items():
            host, port = hostPort
            d = ping(host, port)
            d.addErrback(log.err)
            d.addCallback(_makeGood, tracker, hostPort)



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

