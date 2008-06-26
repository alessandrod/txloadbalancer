from twisted.web import static
from twisted.web import server
from twisted.application import service
from twisted.application import internet

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
hosts = [
    ('lorien', 7001),
    ('lorien', 7002),
    ('lorien', 7003),
    ('lorien', 7004),
    ]

lbType = 'leastconns'

application = service.Application('Demo Web Server')

# the config file for this would only contain a single group (never any more)
# with a series of hosts to proxy
director = manager.ProxyManager(configFile)
tracker = manager.HostTracking(groupConfig)

lbs = txervice.LoadBalancedService()
lbs.addServiceParent(application)
lbs.proxiesFactory(hosts, lbType, director, tracker)

site = server.Site(static.File('./data'))
server = internet.TCPServer(8080, site)

# non-load-balanced, we do the following
lbs.setPrimaryService(server)

# in a load-balanced scenario, we set the ProxyManager as the primary service
