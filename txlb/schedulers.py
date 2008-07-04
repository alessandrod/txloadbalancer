import random
import itertools


rand = 'rand'
roundr= 'roundr'
leastc = 'leastc'
weightr = 'weightr'
weightlc = 'weightlc'
sticky = 'sticky'


def schedulerFactory(lbType, tracker):
    """
    A dispatch function for a service's scheduler.
    """
    if lbType == rand:
        return RandomScheduler(tracker)
    elif lbType == roundr:
        return RoundRobinScheduler(tracker)
    elif lbType == leastc:
        return LeastConnsScheduler(tracker)
    elif lbType == weightr:
        return RandomWeightedScheduler(tracker)
    else:
        raise ValueError, "Unknown scheduler type `%s'" % lbType



class BaseScheduler(object):
    """
    schedulers need the following:
        * access to a proxy's hosts
        * a proxy's open connections
        * the "lastclose" for a host (don't know what that is yet)
    """


    def __init__(self, tracker):
        self.tracker = tracker
        self.tracker.scheduler = self


    def hasHost(self):
        """

        """
        if self.tracker.available.keys():
            return True
        return False



class RandomScheduler(BaseScheduler):
    """
    Select a random proxied host to receive the next request.
    """
    schedulerName = rand


    def nextHost(self, clientAddr):
        if not self.hasHost():
            return
        pick = random.choice(self.hosts)
        return pick



class RoundRobinScheduler(BaseScheduler):
    """
    This scheduler presents a simple algorighm for selecting hosts based on
    nothing other than who's next in the list.
    """
    schedulerName = roundr
    counter = 0


    def nextHost(self, clientAddr):
        if not self.hasHost():
            return
        if self.counter >= len(self.tracker.hosts):
            self.counter = 0
        if self.tracker.hosts:
            d = self.tracker.hosts[self.counter]
            self.counter += 1
            return d



class LeastConnsScheduler(BaseScheduler):
    """
    This scheduler passes the connection to the destination with the least
    number of current open connections. If multiple machines have the same
    number of open connections, send to the least recently used.
    """
    schedulerName = leastc
    counter = 0


    def nextHost(self, clientAddr):
        if not self.hasHost():
            return
        hosts = [(x[1], self.tracker.lastclose.get(x[0],0), x[0])
                 for x in self.tracker.available.items()]
        hosts.sort()
        return hosts[0][2]


class RandomWeightedScheduler(BaseScheduler):
    """
    This scheduler passes the connection in a semi-random fashion, with the
    highest likelihood of selection going to the host with the largest weight
    value.

    In particular, it uses hosts and their associated weights to build a
    "simulated population" of hosts. These to not get place into memory
    en-masse, thanks to the existence of iterators. A single host in the
    "population" is chosen, with hosts of greater weights being selected more
    often (over time).
    """
    schedulerName = weightr


    def nextHost(self, clientAddr):
        if not self.hasHost():
            return
        group = self.tracker.group
        # hosts is a list of (host, port) tuples
        # XXX
        # this is pretty slow... perhaps the weight data should also be stored
        # on the tracker object and we should put the getWeightDistribution and
        # getWeights methods on this scheduler...
        # XXX
        # or we can cache the computed values and refresh them in a tracker
        hosts = self.tracker.available.keys()
        population = group.getWeightDistribution(hostPorts=hosts)
        populationSize = sum([weight for hostPort, weight
            in group.getWeights().items() if hostPort in hosts])
        index = random.randint(0, populationSize - 1)
        return itertools.islice(population, index, None).next()
        

