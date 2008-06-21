from twisted.application import service
from twisted.application import internet
from twisted.application import strports

from pydirector.manager import checkBadHosts

application = service.Application('PyDirector')

# set up the director
director = None

# set up the web server

# set up the manager timer service
checker = internet.TimerService(interval, checkBadHosts, director)
checker.setServiceParent(application)

