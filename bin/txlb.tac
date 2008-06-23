import resource

from txlb.application import setup

configFile = './etc/config.xml'
resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
application = setup(configFile)
