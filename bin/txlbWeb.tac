"""
This is an example of how you would use the nascent, still-developing
load-balancing API in your own Twisted application.

This means load-balancing at the software level, with no extra daemons to run
and manage. You get the load-balancing for "free", built-in to your
application.

There are three things you need in order for your application to offer a
load-balanced service:
    1) a configuration that indicate the proxy, groups(s), and hosts
    2) a proxy manager object
    3) a load-balancing service (twisted.application.service.IService)
"""
from twisted.web import static
from twisted.web import server
from twisted.application import service
from twisted.application import internet

from txlb import model
from txlb import manager
from txlb.model import HostMapper as Host
from txlb.schedulers import roundr, leastc
from txlb.application.service import LoadBalancedService


servicePort = 8080

# one configuration option: use the model classes directly and map out the
# structure you want, explicitly
proxyServices = [
    model.ProxyService(
        'web', addresses=[('localhost', servicePort)],
        groups=[
            model.ProxyGroup('prod', leastc, enabled=True,
                hosts=[
                    model.ProxyHost('host1', '127.0.0.1', port=7001),
                    model.ProxyHost('host2', '127.0.0.1', port=7002),
                    model.ProxyHost('host3', '127.0.0.1', port=7003),
            ]),
            model.ProxyGroup('test', roundr, enabled=True,
                hosts=[
                    model.ProxyHost('host4', '127.0.0.1', port=7004),
                    model.ProxyHost('host5', '127.0.0.1', port=7005),
                    model.ProxyHost('host6', '127.0.0.1', port=7006),
            ]),
        ]),
    ]


# another configuration option: use the host mapper and make things very easy
# to read
proxyServices = [
    Host('web', '127.0.0.1:8080', 'prod', leastc, 'host1', '127.0.0.1:7001', True),
    Host('web', '127.0.0.1:8080', 'prod', leastc, 'host2', '127.0.0.1:7002'),
    Host('web', '127.0.0.1:8080', 'prod', leastc, 'host3', '127.0.0.1:7003'),
    Host('web', '127.0.0.1:8080', 'test', roundr, 'host4', '127.0.0.1:7004', False),
    Host('web', '127.0.0.1:8080', 'test', roundr, 'host5', '127.0.0.1:7005'),
    Host('web', '127.0.0.1:8080', 'test', roundr, 'host6', '127.0.0.1:7006'),
]


application = service.Application('Demo Web Server')

# here's what makes your application load-balacning
pm = manager.proxyManagerFactory(proxyServices)
lbs = LoadBalancedService()
lbs.proxiesFactory(pm)
lbs.setServiceParent(application)

site = server.Site(static.File('/Users/oubiwann/Sites'))
server = internet.TCPServer(servicePort, site)

# for load-balancing on this server, with different processes that have been
# started up independently, as configured above in the ProxyHost model
# instances
lbs.setPrimaryService(server)

# XXX need to add code for making the Proxy the primary service ...
