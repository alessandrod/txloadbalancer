from twisted.web import static
from twisted.web import server
from twisted.application import service
from twisted.application import internet

from txlb import model
from txlb import manager
from txlb.application import service as txervice


servicePort = 8080

proxyServices = [
    model.ProxyService(
        'test proxy service', addresses=[('localhost', servicePort)],
        groups=[
            model.ProxyGroup('test proxy group', 'leastconns', enabled=True,
                hosts=[
                    model.ProxyHost('myhost1', '127.0.0.1', port=7001),
                    model.ProxyHost('myhost2', '127.0.0.1', port=7002),
                    model.ProxyHost('badhost2', '127.0.0.1', port=7003),
            ]),
        ]),
    ]


application = service.Application('Demo Web Server')

pm = manager.proxyManagerFactory(proxyServices)
lbs = txervice.LoadBalancedService()
lbs.proxiesFactory(pm)
lbs.setServiceParent(application)

site = server.Site(static.File('./data'))
server = internet.TCPServer(servicePort, site)

# non-load-balanced, we do the following
lbs.setPrimaryService(server)

# in a load-balanced scenario, we set the ProxyManager as the primary service
