import time
import random

from txlb import util
from txlb import logging

roundr= 0
rand = 1
leastc = 2
weighted = 3

def schedulerFactory(lbType, tracker):
    """
    A dispatch function for a service's scheduler.
    """
    if lbType == "random":
        return RandomScheduler(tracker)
    elif lbType == "leastconns":
        return LeastConnsScheduler(tracker)
    elif lbType == "roundrobin":
        return RoundRobinScheduler(tracker)
    elif lbType == "leastconnsrr":
        return LeastConnsRRScheduler(tracker)
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
    schedulerName = "random"

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
    schedulerName = "roundrobin"
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
    number of current open connections. This is a very cheap and quite accurate
    method of load balancing.
    """
    schedulerName = "leastconns"
    counter = 0

    def nextHost(self, client_addr):
        if not self.tracker.available.keys():
            return None
        hosts = [(x[1],x[0]) for x in self.tracker.available.items()]
        hosts.sort()
        return hosts[0][1]


class LeastConnsRRScheduler(BaseScheduler):
    """
    The basic LeastConnsScheduler has a problem - it sorts by open connections,
    then by hostname. So hostnames that are earlier in the alphabet get many
    many more hits. This is suboptimal.
    """
    schedulerName = "leastconnsrr"
    counter = 0

    def nextHost(self, client_addr):
        if not self.tracker.available.keys():
            return None
        hosts = [(x[1], self.tracker.lastclose.get(x[0],0), x[0])
                            for x in self.tracker.available.items()]
        hosts.sort()
        return hosts[0][2]

