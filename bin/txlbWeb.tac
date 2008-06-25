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

lbs = txervice.LoadBalancedService()
lbs.addServiceParent(application)
lbs.proxiesFactory(hosts, lbType)

site = server.Site(static.File('./data'))
server = internet.TCPServer(8080, site)

lbs.setPrimaryService(server)
