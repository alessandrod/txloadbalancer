import random


rand = 10
roundr= 20
leastc = 30
weightr = 40
weightlc = 41
sticky = 50


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



class RandomScheduler(BaseScheduler):
    """
    Select a random proxied host to receive the next request.
    """
    schedulerName = rand


    def nextHost(self, client_addr):
        if self.hosts:
            pick = random.choice(self.hosts)
            return pick
        else:
            return None



class RoundRobinScheduler(BaseScheduler):
    """
    This scheduler presents a simple algorighm for selecting hosts based on
    nothing other than who's next in the list.
    """
    schedulerName = roundr
    counter = 0


    def nextHost(self, client_addr):
        if not self.tracker.hosts:
            return None
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


    def nextHost(self, client_addr):
        if not self.tracker.available.keys():
            return None
        hosts = [(x[1], self.tracker.lastclose.get(x[0],0), x[0])
                            for x in self.tracker.available.items()]
        hosts.sort()
        return hosts[0][2]


class RandomWeightedScheduler(BaseScheduler):
    """
    This scheduler passes the connection by random, with the highest likelihood
    of selection going to the host with the largest weight value.
    """
    schedulerName = weightr


    def nextHost(self, client_addr):
        pass
