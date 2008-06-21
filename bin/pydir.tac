import resource

from twisted.application import service
from twisted.application import internet
from twisted.application import strports

from pydirector import main
from pydirector.manager import checkBadHosts

resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))

application = service.Application('PyDirector')

# set up the director
configFile = './config.xml'
director = main.Director(configFile)

# set up the web server
admin = None

# set up the manager timer service
checkInterval = 120
checker = internet.TimerService(checkInterval, checkBadHosts, director)
checker.setServiceParent(application)

