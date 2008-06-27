from twisted.web import static
from twisted.web import server
from twisted.application import service
from twisted.application import internet

from txlb import model
from txlb import manager
from txlb.application import service as txervice

# perhaps the schedulers *should* have the list of hosts, since they may need
# to know which ones are prefered for weighting... so maybe host information
# should have the following attributes encoded:
#   * hostname/ip
#   * port
#   * weighting
#   * filetype (file types that the host accepts, determined by extension)
#   * protocol (protocols that the host accepts, determined by URL scheme, if
#              applicable)

proxyServices =[
    model.ProxyService(
        'test proxy service', addresses=[('localhost', 8080)],
        groups=[
            model.ProxyGroup('test proxy group', 'leastconns', enabled=True,
                hosts=[
                    model.ProxyHost('myhost1', '127.0.0.1', port=7001),
                    model.ProxyHost('myhost2', '127.0.0.1', port=7002),
                    model.ProxyHost('badhost2', '127.0.0.1', port=7003),
            ]),
        ]),
    ]

pm = manager.proxyManagerFactory(proxyServices)

application = service.Application('Demo Web Server')

lbType = proxyServices[0].getEnabledGroup().lbType
tracker = pm.getTracker(
    proxyServices[0].name,
    proxyServices[0].getEnabledGroup().name)
lbs = txervice.LoadBalancedService(lbType, tracker)
lbs.proxiesFactory(pm)
lbs.setServiceParent(application)

site = server.Site(static.File('./data'))
server = internet.TCPServer(8080, site)

# non-load-balanced, we do the following
lbs.setPrimaryService(server)

# in a load-balanced scenario, we set the ProxyManager as the primary service
