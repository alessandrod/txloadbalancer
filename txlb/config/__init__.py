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



class ConfigError(Exception):
    """

    """



class ServiceError(ConfigError):
    """

    """



class GroupError(ServiceError):
    """

    """



class BaseConfig(object):
    """

    """
    tag = u''


    def getObjects(self):
        """

        """
        return self.__dict__.items()


class HostConfig(BaseConfig):
    """

    """
    tag = u'host'


    def __init__(self, name, ip, weight=1):
        self.name = name
        self.weight = int(weight)
        if type(ip) is type(u''):
            self.ip = ip.encode('ascii')
        else:
            self.ip = ip


    def toXML(self):
        """

        """
        attrs = u''
        for attrName, attrVal in self.getObjects():
            attrs += '%s="%s" ' % (attrName, attrVal)
        data = {'name': self.tag, 'attrs': attrs}
        return "<%(name)s %(attrs)s/>" % data



class GroupConfig(BaseConfig):
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


    def addHost(self, name, ip, weight=1):
        self.hosts[name] = HostConfig(name, ip, weight)


    def delHost(self, name):
        del self.hosts[name]



class ServiceConfig(BaseConfig):
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
            weight = 1
            if host.hasAttribute('weight'):
                weight = host.getAttribute('weight')
            newgroup.addHost(name, host.getAttribute('ip'), weight)
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



class AdminUserConfig(BaseConfig):
    """

    """


    def __init__(self):
        self.name = ''
        self.password = ''
        self.access = ''


    def checkPW(self, password):
        return util.checkCryptPassword(password, self.password)



class ManagerConfig(BaseConfig):
    """

    """


    def __init__(self):
        self.hostCheckInterval = 120



class AdminConfig(BaseConfig):
    """

    """


    def __init__(self):
        self.webListen = None
        self.webEnable = False
        self.webSecure = False
        self.webRefresh = 30
        self.sshListen = 2222
        self.sshEnable = False
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


    def loadWeb(self, webNode):
        if webNode.hasAttribute('listen'):
            self.webListen = util.splitHostPort(webNode.getAttribute('listen'))
        if webNode.hasAttribute('enable'):
            self.webEnable = util.boolify(webNode.getAttribute('enable'))
        if webNode.hasAttribute('secure'):
            self.webSecure = util.boolify(webNode.getAttribute('secure'))
        if webNode.hasAttribute('refresh'):
            self.webRefresh = util.boolify(webNode.getAttribute('refresh'))


    def loadSSH(self, sshNode):
        if sshNode.hasAttribute('listen'):
            self.sshListen = util.splitHostPort(sshNode.getAttribute('listen'))
        if sshNode.hasAttribute('enable'):
            self.sshEnable = util.boolify(sshNode.getAttribute('enable'))


    def loadUser(self, userNode):
        name = userNode.getAttribute('name')
        password = userNode.getAttribute('password')
        access = userNode.getAttribute('access')
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
        for child in admin.childNodes:
            if child.nodeName in legalCommentSections:
                continue
            elif child.nodeName == u'user':
                adminCfg.loadUser(child)
            elif child.nodeName == u'web':
                adminCfg.loadWeb(child)
            elif child.nodeName == u'ssh':
                adminCfg.loadSSH(child)
            else:
                msg = "Only 'web', 'ssh', or 'user' should be in admin block"
                raise ConfigError, msg
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

