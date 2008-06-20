#
# Copyright (c) 2002-2004 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pdschedulers.py,v 1.16 2004/12/14 13:31:39 anthonybaxter Exp $
#

import sys, time
if sys.version_info < (2,2):
    class object: pass

import pdconf, pdlogging

def createScheduler(groupConfig):
    schedulerName = groupConfig.scheduler
    if schedulerName == "random":
        return RandomScheduler(groupConfig)
    elif schedulerName == "leastconns":
        return LeastConnsScheduler(groupConfig)
    elif schedulerName == "roundrobin":
        return RoundRobinScheduler(groupConfig)
    elif schedulerName == "leastconnsrr":
        return LeastConnsRRScheduler(groupConfig)
    else:
        raise ValueError, "Unknown scheduler type `%s'"%schedulerName

class BaseScheduler:

    schedulerName = "base"

    def __init__(self, groupConfig):
        self.hosts = []
        self.hostnames = {}
        self.badhosts = {}
        self.open = {}
        self.openconns = {}
        self.totalconns = {}
        self.lastclose = {}
        self.loadConfig(groupConfig)

    def loadConfig(self, groupConfig):
        self.group = groupConfig
        hosts = self.group.getHosts()
        for host in hosts:
            self.newHost(host.ip, host.name)
        #print self.hosts

    def getStats(self, verbose=0):
        out = {}
        out['open'] = {}
        out['totals'] = {}
        hc = self.openconns.items()
        hc.sort()
        for h,c in hc:
            out['open']['%s:%s'%h] = c
        hc = self.totalconns.items()
        hc.sort()
        for h,c in hc:
            out['totals']['%s:%s'%h] = c
        bh = self.badhosts
        out['bad'] = bh
        return out

    def showStats(self, verbose=1):
        out = []
        out.append( "%d open connections"%len(self.open.keys()) )
        hc = self.openconns.items()
        hc.sort()
        out = out + [str(x) for x in hc]
        if verbose:
            oh = [x[1] for x in self.open.values()]
            oh.sort()
            out = out + [str(x) for x in oh]
        return "\n".join(out)

    def getHost(self, s_id, client_addr=None):
        from time import time
        host = self.nextHost(client_addr)
        if host:
            cur = self.openconns.get(host)
            self.open[s_id] = (time(),host)
            self.openconns[host] = cur+1
            return host
        else:
            return None

    def getHostNames(self):
        return self.hostnames

    def doneHost(self, s_id):
        try:
            t,host = self.open[s_id]
        except KeyError:
            #print "Couldn't find %s in %s"%(repr(s_id), repr(self.open.keys()))
            return
        del self.open[s_id]
        cur = self.openconns.get(host)
        if cur is not None:
            self.openconns[host] = cur - 1
            self.totalconns[host] += 1
        self.lastclose[host] = time.time()

    def newHost(self, ip, name):
        if type(ip) is not type(()):
            ip = pdconf.splitHostPort(ip)
        self.hosts.append(ip)
        self.hostnames[ip] = name
        self.hostnames['%s:%d'%ip] = name
        self.openconns[ip] = 0
        self.totalconns[ip] = 0

    def delHost(self, ip=None, name=None, activegroup=0):
        "remove a host"
        if ip is not None:
            if type(ip) is not type(()):
                ip = pdconf.splitHostPort(ip)
        elif name is not None:
            for ip in self.hostnames.keys():
                if self.hostnames[ip] == name:
                    break
            raise ValueError, "No host named %s"%(name)
        else:
            raise ValueError, "Neither ip nor name supplied"
        if activegroup and len(self.hosts) == 1:
            return 0
        if ip in self.hosts:
            self.hosts.remove(ip)
            del self.hostnames[ip]
            del self.openconns[ip]
            del self.totalconns[ip]
        elif self.badhosts.has_key(ip):
            del self.badhosts[ip]
        else:
            raise ValueError, "Couldn't find host"
        return 1

    def deadHost(self, s_id, reason=''):
        from time import time
        t,host = self.open[s_id]
        if host in self.hosts:
            pdlogging.log("marking host %s down (%s)\n"%(str(host), reason),
                            datestamp=1)
            self.hosts.remove(host)
        if self.openconns.has_key(host):
            del self.openconns[host]
        if self.totalconns.has_key(host):
            del self.totalconns[host]
        self.badhosts[host] = (time(), reason)
        # make sure we also mark this session as done.
        self.doneHost(s_id)

    def nextHost(self):
        raise NotImplementedError

class RandomScheduler(BaseScheduler):
    schedulerName = "random"

    def nextHost(self, client_addr):
        import random
        if self.hosts:
            pick = random.choice(self.hosts)
            return pick
        else:
            return None

class RoundRobinScheduler(BaseScheduler):
    schedulerName = "roundrobin"
    counter = 0

    def nextHost(self, client_addr):
        if not self.hosts:
            return None
        if self.counter >= len(self.hosts):
            self.counter = 0
        if self.hosts:
            d = self.hosts[self.counter]
            self.counter += 1
            return d

class LeastConnsScheduler(BaseScheduler):
    """
        This scheduler passes the connection to the destination with the
        least number of current open connections. This is a very cheap
        and quite accurate method of load balancing.
    """
    schedulerName = "leastconns"
    counter = 0

    def nextHost(self, client_addr):
        if not self.openconns.keys():
            return None
        hosts = [ (x[1],x[0]) for x in self.openconns.items() ]
        hosts.sort()
        return hosts[0][1]

class LeastConnsRRScheduler(BaseScheduler):
    """
        The basic LeastConnsScheduler has a problem - it sorts by
        open connections, then by hostname. So hostnames that are
        earlier in the alphabet get many many more hits. This is
        suboptimal.
    """
    schedulerName = "leastconnsrr"
    counter = 0

    def nextHost(self, client_addr):
        if not self.openconns.keys():
            return None
        hosts = [ (x[1], self.lastclose.get(x[0],0), x[0])
                            for x in self.openconns.items() ]
        hosts.sort()
        return hosts[0][2]

