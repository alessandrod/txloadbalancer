import resource

from twisted.web import server
from twisted.application import service
from twisted.application import internet
from twisted.application import strports

from pydirector import main
from pydirector.web import admin
from pydirector.manager import checkBadHosts

resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))

application = service.Application('PyDirector')
services = service.IServiceCollection(application)

# set up the director
configFile = './config.xml'
director = main.Director(configFile)

# set up the web server
site = server.Site(admin.AdminServer(director))
if director.conf.admin.secure:
    admin = None
else:
    admin = internet.TCPServer(director.conf.admin.listen[1], site)
admin.setServiceParent(services)

# set up the manager timer service
# XXX this interval needs to be in the configuration
checkInterval = 120
checker = internet.TimerService(checkInterval, checkBadHosts, director)
checker.setServiceParent(services)

