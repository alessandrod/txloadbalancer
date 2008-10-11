import os

from twisted.python import log
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import protocol

from txlb import util


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
        """
        The private callback function for the pinger.
        """
        # remember that the result is from a deferred list, so it's a a list of
        # (Bool, result/failure) tuples; if there are any problems at all
        # connecting to the host, we don't want to put it back into rotation
        if False in [x[0] for x in result]:
            log.msg("Host %s is still down.\n" % str(hostPort))
            return
        log.msg("Host is back up; re-adding %s ...\n" % str(hostPort))
        tracker.resetHost(hostPort)

    if not configuration.manager.hostCheckEnabled:
        return
    for name, service in director.getServices():
        # since all proxies for a service share a tracker,
        # we only need to check the first proxy.
        group = service.getEnabledGroup()
        tracker = director.getTracker(name, group.name)
        badHosts = tracker.badhosts
        allHostPorts = [(host.hostname, host.port)
                      for name, host in group.getHosts()]
        # if there are no good hosts, we need to put them all back into
        # rotation
        if not set(allHostPorts).symmetric_difference(badHosts.keys()):
            tracker.resetBadHosts()
            log.msg("All hosts are down! Forcing them back into rotation ...")
            return
        #import pdb;pdb.set_trace()
        for hostPort, timeAndError in badHosts.items():
            host, port = hostPort
            d = ping(host, port)
            d.addErrback(log.err)
            d.addCallback(_makeGood, tracker, hostPort)


def checkConfigChanges(configuration, director):
    """
    A scheduled checker for configration changes.
    """
    if not configuration.manager.configCheckEnabled:
        return
    util.saveConfig(configuration, director)

