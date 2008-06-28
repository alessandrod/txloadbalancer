from twisted.trial import unittest

from txlb import model
from txlb.manager import HostTracking
from txlb.schedulers import schedulerFactory, roundr, leastc

class HostTrackingTests(unittest.TestCase):
    """

    """
    def setUp(self):
        """

        """
        group1 = model.ProxyGroup('test_group1', roundr, True)
        group1.addHost(model.ProxyHost('goodhost1', 'ip1', 1))
        group1.addHost(model.ProxyHost('goodhost2', 'ip1', 2))
        group1.addHost(model.ProxyHost('badhost1', 'ip1', 3))
        group1.addHost(model.ProxyHost('badhost2', 'ip1', 4))
        self.group1 = group1

        group2 = model.ProxyGroup('test_group2', leastc, True)
        group2.addHost(model.ProxyHost('goodhost3', 'ip1', 5))
        group2.addHost(model.ProxyHost('goodhost4', 'ip1', 6))
        group2.addHost(model.ProxyHost('badhost3', 'ip1', 7))
        group2.addHost(model.ProxyHost('badhost4', 'ip1', 8))
        self.group2 = group2

        self.ht1 = HostTracking(self.group1)
        self.ht2 = HostTracking(self.group2)

        self.s1 = schedulerFactory(self.ht1.group.lbType, self.ht1)
        self.s2 = schedulerFactory(self.ht2.group.lbType, self.ht2)

    def test_schedulerName(self):
        """

        """
        self.assertEquals(self.ht1.group.lbType, self.group1.lbType)

    def test_trackerScheduler(self):
        """

        """
        self.assertEquals(self.ht1.scheduler, self.s1)

    def test_initialHosts(self):
        """

        """
        expected = [
            'badhost1', 'badhost1', 'badhost2', 'badhost2', 'goodhost1',
            'goodhost1', 'goodhost2', 'goodhost2']
        hostnames = self.ht1.getHostNames().values()
        hostnames.sort()
        self.assertEquals(hostnames, expected)
        expected = [
            'ip1:1', 'ip1:2', 'ip1:3', 'ip1:4', ('ip1', 1), ('ip1', 2),
            ('ip1', 3), ('ip1', 4)]
        hosts = self.ht1.getHostNames().keys()
        hosts.sort()
        self.assertEquals(hosts, expected)

    def test_initialStats(self):
        """
        We can't use self.ht1, because it might be contaminated by other tests.
        """
        ht1 = HostTracking(self.group1)
        s1 = schedulerFactory(ht1.group.lbType, ht1)
        stats = ht1.getStats()
        self.assertEquals(len(stats['bad'].keys()), 0)
        self.assertEquals(sum(stats['openconns'].values()), 0)
        self.assertEquals(sum(stats['totals'].values()), 0)

    def test_openHostStats(self):
        """
        We can't use self.ht1, because it might be contaminated by other tests.
        """
        fakeSenderFactory = object()
        ht1 = HostTracking(self.group1)
        s1 = schedulerFactory(ht1.group.lbType, ht1)
        host = ht1.getHost(fakeSenderFactory)
        stats = ht1.getStats()
        self.assertEquals(len(stats['bad'].keys()), 0)
        self.assertEquals(sum(stats['openconns'].values()), 1)
        self.assertEquals(sum(stats['totals'].values()), 0)

    def test_deadHostStats(self):
        """

        """
        badHost = ('ip1', 3)
        time = None
        fakeSenderFactory = object()
        ht1 = HostTracking(self.group1)
        s1 = schedulerFactory(ht1.group.lbType, ht1)
        ht1.openconns[fakeSenderFactory] = (time, badHost)
        ht1.deadHost(fakeSenderFactory, doLog=False)
        stats = ht1.getStats()
        self.assertEquals(len(stats['bad'].keys()), 1)
        self.assertEquals(sum(stats['openconns'].values()), 0)
        self.assertEquals(sum(stats['totals'].values()), 0)

    def test_getHostRoundRobin(self):
        """

        """
        sequence = [self.ht1.getHost(None) for x in xrange(10)]
        # compare cycle 1 and 2
        self.assertEquals(sequence[0], sequence[4])
        self.assertEquals(sequence[1], sequence[5])
        self.assertEquals(sequence[2], sequence[6])
        self.assertEquals(sequence[3], sequence[7])
        # compare cycle 1 and 3
        self.assertEquals(sequence[0], sequence[8])
        self.assertEquals(sequence[1], sequence[9])

    def test_preserveDeadHostStats(self):
        """

        """
        time = None
        ht1 = HostTracking(self.group1)
        s1 = schedulerFactory(ht1.group.lbType, ht1)
        # let's cycle through all the hosts twice
        fakeSenderFactories = [object() for x in xrange(8)]
        sequence = [ht1.getHost(x) for x in fakeSenderFactories]
        # check the stats
        stats = ht1.getStats()
        self.assertEquals(len(stats['bad'].keys()), 0)
        self.assertEquals(sum(stats['openconns'].values()), 8)
        self.assertEquals(sum(stats['totals'].values()), 0)
        # finish them up
        [ht1.doneHost(x) for x in fakeSenderFactories]
        # check the clenaup stats
        stats = ht1.getStats()
        self.assertEquals(len(stats['bad'].keys()), 0)
        self.assertEquals(sum(stats['openconns'].values()), 0)
        self.assertEquals(sum(stats['totals'].values()), 8)
        # now let's do a bad host
        fakeSenderFactory = object()
        host = ht1.getHost(fakeSenderFactory)
        stats = ht1.getStats()
        # make sure that the bad host is listed in the open connections
        self.assertEquals(sum(stats['openconns'].values()), 1)
        ht1.openconns[fakeSenderFactory] = (time, host)
        ht1.deadHost(fakeSenderFactory, doLog=False)
        stats = ht1.getStats()
        # make sure that the previous stats for the bad host are not deleted
        self.assertEquals(sum(stats['totals'].values()), 8)

