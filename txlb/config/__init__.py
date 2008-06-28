import inspect
from crypt import crypt
from xml.dom import minidom

from txlb import util
from txlb import logging
from txlb import schedulers


legalConfigSections = [
    u'service',
    u'admin',
    u'logging',
    u'manager',
    u'control',
    ]



legalCommentSections = [
    'note',
    '#text',
    '#comment',
    '#cdata-section',
    ]



def getDefaultArgs(methodObj):
    """

    """
    arglist, vaarg, kwarg, defargs = inspect.getargspec(methodObj.im_func)
    arglist.reverse()
    defargs = list(defargs)
    defargs.reverse()
    ad = {}
    for a,v in zip(arglist, defargs):
        ad[a] = v
    return ad



class ConfigError(Exception):
    """

    """



class ServiceError(ConfigError):
    """

    """



class GroupError(ServiceError):
    """

    """



class HostConfig(object):
    """

    """


    def __init__(self, name, ip):
        self.name = name
        if type(ip) is type(u''):
            self.ip = ip.encode('ascii')
        else:
            self.ip = ip



class GroupConfig(object):
    """

    """


    def __init__(self, name):
        self.name = name
        self.scheduler = None
        self.hosts = {}


    def getHost(self,name):
        return self.hosts[name]


    def getHostNamess(self):
        return self.hosts.keys()


    def getHosts(self):
        return self.hosts.values()


    def addHost(self, name, ip):
        self.hosts[name] = HostConfig(name, ip)


    def delHost(self, name):
        del self.hosts[name]



class ServiceConfig(object):
    """

    """

    def __init__(self, name):
        self.name = name
        self.groups = {}
        self.listen = []
        self.enabledgroup = None


    def loadGroup(self, groupobj):
        groupName = groupobj.getAttribute('name')
        newgroup = GroupConfig(groupName)
        schedulerStr = groupobj.getAttribute('scheduler')
        newgroup.scheduler = getattr(schedulers, schedulerStr)
        cc = 0
        for host in groupobj.childNodes:
            if host.nodeName in legalCommentSections:
                continue
            if host.nodeName != u'host':
                raise ConfigError, \
                    "expected 'host', got '%s'"%host.nodeName
            name = host.getAttribute('name')
            if not name: name = 'host.%s'%cc
            newgroup.addHost(name, host.getAttribute('ip'))
            cc += 1
        self.groups[groupName] = newgroup


    def getGroup(self, groupName):
        return self.groups.get(groupName)


    def getGroups(self):
        return self.groups.values()


    def getGroupNames(self):
        return self.groups.keys()


    def getEnabledGroup(self):
        return self.groups.get(self.enabledgroup)


    def checkSanity(self):
        if not self.name:
            raise ServiceError, "no name set"
        if not self.listen:
            raise ServiceError, "no listen address set"
        if not self.groups:
            raise ServiceError, "no host groups"
        if not self.enabledgroup:
            raise ServiceError, "no group enabled"
        if not self.groups.get(self.enabledgroup):
            msg = "enabled group '%s' not defined" % self.enabledgroup
            raise GroupError, msg
        for group in self.groups.values():
            if not group.name:
                raise GroupError, "no group name set"
            if group.scheduler == None:
                raise GroupError, "no scheduler set for %s" % group.name
            if not group.hosts:
                raise GroupError, "no hosts set for %s" % group.name



class AdminUserConfig(object):
    """

    """


    def __init__(self):
        self.name = ''
        self.password = ''
        self.access = ''


    def checkPW(self, password):
        if crypt(password, self.password[:2]) == self.password:
            return True
        return False


    def checkAccess(self, methodObj, argdict):
        a = getDefaultArgs(methodObj)
        required = a.get('Access', 'NoAccess')
        if required == "Read" and self.access in ('full', 'readonly'):
            return True
        elif required == "Write" and self.access == 'full':
            return True
        return False



class ManagerConfig(object):
    """

    """


    def __init__(self):
        self.hostCheckInterval = 120



class AdminConfig(object):
    """

    """


    def __init__(self):
        self.listen = None
        self.secure = False
        self.refresh = 30
        self.userdb = {}


    def addUser(self, name, password, access):
        u = AdminUserConfig()
        u.name = name
        u.password = password
        u.access = access
        self.userdb[name] = u


    def delUser(self, name):
        if self.userdb.has_key(name):
            del self.userdb[name]
            return 1
        else:
            return 0


    def loadUser(self, userobj):
        name = userobj.getAttribute('name')
        password = userobj.getAttribute('password')
        access = userobj.getAttribute('access')
        self.addUser(name, password, access)


    def getUser(self, name):
        return self.userdb.get(name)


    def getUsers(self):
        return self.userdb.values()


    def getUserNames(self):
        return self.userdb.keys()


class Config(object):
    """

    """


    def __init__(self, filename=None, xml=None):
        self.services = {}
        self.admin = None
        self.manager = None
        self.dom = None
        self.socket = None
        dom = self._loadDOM(filename, xml)
        if dom.nodeName != 'pdconfig':
            msg = "expected top level 'pdconfig', got '%s'" % (dom.nodeName)
            raise ConfigError, msg
        for item in dom.childNodes:
            if item.nodeName in legalCommentSections:
                continue
            if item.nodeName not in legalConfigSections:
                msg = "Got '%s', not legal section name." % item.nodeName
                raise ConfigError, msg
            if item.nodeName == u'service':
                self.loadService(item)
            elif item.nodeName == u'admin':
                if self.admin is None:
                    self.loadAdmin(item)
                else:
                    raise ConfigError, "only one 'admin' block allowed"
            elif item.nodeName == u'manager':
                self.loadManager(item)
            elif item.nodeName == u'logging':
                logging.initlog(item.getAttribute('file'))
            elif item.nodeName == u'control':
                self.socket = item.getAttribute('socket')
        if self.manager == None:
            self.manager = ManagerConfig()


    def _loadDOM(self, filename, xml):
        if filename is not None:
            xml = open(filename).read()
        elif xml is None:
            raise ConfigError, "need filename or xml"
        self.dom = minidom.parseString(xml)
        return self.dom.childNodes[0]


    def loadAdmin(self, admin):
        adminCfg = AdminConfig()
        adminCfg.listen = util.splitHostPort(admin.getAttribute('listen'))
        if admin.hasAttribute('secure'):
            adminCfg.secure = True
        if admin.hasAttribute('refresh'):
            adminCfg.refresh = int(admin.getAttribute('refresh'))
        for user in admin.childNodes:
            if user.nodeName in legalCommentSections:
                continue
            if user.nodeName == u'user':
                adminCfg.loadUser(user)
            else:
                raise ConfigError, "only expect to see users in admin block"
        self.admin = adminCfg


    def loadManager(self, manager):
        manageCfg = ManagerConfig()
        if manager.hasAttribute('hostCheckInterval'):
            manageCfg.hostCheckInterval = float(manager.getAttribute(
                'hostCheckInterval'))
        self.manager = manageCfg


    def getService(self, serviceName):
        return self.services.get(serviceName)


    def getServices(self):
        return self.services.values()


    def getServiceNames(self):
        return self.services.keys()


    def loadService(self, service):
        serviceName = service.getAttribute('name')
        serviceCfg = ServiceConfig(serviceName)
        for c in service.childNodes:
            if c.nodeName in legalCommentSections:
                continue
            if c.nodeName == u'listen':
                serviceCfg.listen.append(c.getAttribute('ip'))
            elif c.nodeName == u'group':
                serviceCfg.loadGroup(c)
            elif c.nodeName == u'enable':
                serviceCfg.enabledgroup = c.getAttribute('group')
            elif c.nodeName == "#comment":
                continue
            else:
                raise ConfigError, "unknown node '%s'"%c.nodeName
        serviceCfg.checkSanity()
        self.services[serviceName] = serviceCfg

