import re
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


    def getProps(self, only=[], skip=[]):
        """

        """
        check = [int, float, list, tuple, str, unicode]
        for key, val in  self.__dict__.items():
            if True in [isinstance(val, x) for x in check]:
                if only and key in only:
                    yield (key, val)
                elif key not in skip:
                    yield (key, val)

    def getXMLAttrs(self, only=[], skip=[], pairs=[]):
        """

        """
        attrs = u''
        if not pairs:
            pairs = self.getProps(only=only, skip=skip)
        for attrName, attrVal in pairs:
            attrs += ' %s="%s"' % (attrName, attrVal)
        return attrs


class HostConfig(BaseConfig):
    """

    """
    type = u'host'


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
        data = {'tag': self.type, 'attrs': self.getXMLAttrs()}
        return "<%(tag)s%(attrs)s />" % data



class GroupConfig(BaseConfig):
    """

    """
    type = u'group'


    def __init__(self, name):
        self.name = name
        self.scheduler = None
        self.hosts = {}
        self.enable = False


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


    def setEnabled(self):
        self.enable = True


    def setDisabled(self):
        self.enable = False


    def isEnabled(self):
        return self.enable


    def toXML(self, padding=''):
        """

        """
        inner = u''
        indent = padding + '  '
        hosts = [(x.name, x) for x in self.getHosts()]
        hosts.sort()
        for hostName, host in hosts:
            inner += indent + '%s\n' % host.toXML()
        data = {
            'tag': self.type,
            'attrs': self.getXMLAttrs(),
            'inner': inner,
            'prepend': padding}
        output = "%(prepend)s<%(tag)s%(attrs)s>\n" % data
        output += "%(inner)s%(prepend)s</%(tag)s>\n" % data
        return output


class ServiceConfig(BaseConfig):
    """

    """
    type = u'service'


    def __init__(self, name):
        self.name = name
        self.groups = {}
        self.listen = []
        self.enabledgroup = None


    def loadGroup(self, groupobj):
        groupName = groupobj.getAttribute('name')
        newgroup = GroupConfig(groupName)
        if (groupobj.hasAttribute('enable') and
            util.boolify(groupobj.getAttribute('enable'))):
            self.enabledgroup = groupName
            newgroup.setEnabled()
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


    def setEnabledGroup(self, groupName):
        oldGroup = self.getEnabledGroup()
        oldGroup.setDisabled()
        newGroup = self.getGroup(groupName)
        newGroup.setEnabled()
        self.enabledgroup = groupName


    def getListeners(self):
        return self.listen


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


    def toXML(self, padding=''):
        """

        """
        inner = u''
        indent = padding + '  '
        listeners = self.getListeners()
        listeners.sort()
        for listen in listeners:
            inner += '%s<listen ip="%s" />\n' % (indent, listen)
        groups = [(x.name, x) for x in self.getGroups()]
        groups.sort()
        for groupName, group in groups:
            inner += group.toXML(indent)
        data = {
            'tag': self.type,
            'attrs': self.getXMLAttrs(skip=['listen', 'enabledgroup']),
            'inner': inner,
            'prepend': padding}
        output = "%(prepend)s<%(tag)s%(attrs)s>\n" % data
        output += "%(inner)s%(prepend)s</%(tag)s>\n" % data
        return output




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
    type = u'manager'


    def __init__(self):
        self.hostCheckInterval = 120
        self.hostCheckEnabled = False
        self.configCheckInterval = 30
        self.configCheckEnabled = False
        self.heartbeatInterval = 60
        self.heartbeatEnabled = False


    def loadHostCheck(self, checkNode):
        if checkNode.hasAttribute('interval'):
            self.hostCheckInterval = float(checkNode.getAttribute('interval'))
        if checkNode.hasAttribute('enable'):
            self.hostCheckEnabled = util.boolify(
                checkNode.getAttribute('enable'))


    def loadConfigCheck(self, checkNode):
        if checkNode.hasAttribute('interval'):
            self.configCheckInterval = float(checkNode.getAttribute('interval'))
        if checkNode.hasAttribute('enable'):
            self.configCheckEnabled = util.boolify(
                checkNode.getAttribute('enable'))


    def loadHeartbeat(self, checkNode):
        if checkNode.hasAttribute('interval'):
            self.heartbeatInterval = float(checkNode.getAttribute('interval'))
        if checkNode.hasAttribute('enable'):
            self.heartbeatEnabled = util.boolify(
                checkNode.getAttribute('enable'))


    def toXML(self, padding=''):
        """

        """
        indent = padding + '  '
        output = u'%s<%s>\n' % (padding, self.type)
        output += '%s<hostCheck interval="%s" enable="%s" />\n' % (
            indent, self.hostCheckInterval, self.hostCheckEnabled)
        output += '%s<configCheck interval="%s" enable="%s" />\n' % (
            indent, self.configCheckInterval, self.configCheckEnabled)
        output += '%s<heartbeat interval="%s" enable="%s" />\n' % (
            indent, self.heartbeatInterval, self.heartbeatEnabled)
        return output + '%s</%s>\n' % (padding, self.type)



class ControlConfig(BaseConfig):
    """

    """
    type = u'control'


    def __init__(self, socket=None):
        self.socket = socket


    def toXML(self, padding=''):
        """

        """
        return '%s<control socket="%s" />\n' % (padding, self.socket)



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
            #self.webListen = util.splitHostPort(webNode.getAttribute('listen'))
            self.webListen = webNode.getAttribute('listen')
        if webNode.hasAttribute('enable'):
            self.webEnable = util.boolify(webNode.getAttribute('enable'))
        if webNode.hasAttribute('secure'):
            self.webSecure = util.boolify(webNode.getAttribute('secure'))
        if webNode.hasAttribute('refresh'):
            self.webRefresh = util.boolify(webNode.getAttribute('refresh'))


    def loadSSH(self, sshNode):
        if sshNode.hasAttribute('listen'):
            #self.sshListen = util.splitHostPort(sshNode.getAttribute('listen'))
            self.sshListen = sshNode.getAttribute('listen')
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


    def toXML(self, padding=''):
        """

        """
        inner = u''
        indent = padding + '  '
        webAttrs = [(re.sub('web', '', x).lower(), y)
            for x, y in self.__dict__.items() if x.startswith('web')]
        web = {
            'tag': 'web',
            'attrs': self.getXMLAttrs(pairs=webAttrs),
            'prepend': indent}
        sshAttrs = [(re.sub('ssh', '', x).lower(), y)
            for x, y in self.__dict__.items() if x.startswith('ssh')]
        ssh = {
            'tag': 'ssh',
            'attrs': self.getXMLAttrs(pairs=sshAttrs),
            'prepend': indent}
        users = []
        for user in self.getUsers():
            userData = {
                'tag': 'user',
                'attrs': user.getXMLAttrs(),
                'prepend': indent}
            users.append(userData)
        for data in [web, ssh] + users:
            inner += '%(prepend)s<%(tag)s%(attrs)s />\n' % data
        data = {
            'tag': 'admin',
            'inner': inner,
            'prepend': padding}
        return '%(prepend)s<%(tag)s>\n%(inner)s%(prepend)s</%(tag)s>\n' % data



class Config(object):
    """

    """
    type = u'config'


    def __init__(self, filename=None, xml=None):
        self.services = {}
        self.admin = None
        self.manager = None
        self.dom = None
        self.control = None
        dom = self._loadDOM(filename, xml)
        if dom.nodeName != 'config':
            msg = "expected top level 'config', got '%s'" % (dom.nodeName)
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
                self.loadControl(item)
        if self.manager == None:
            self.manager = ManagerConfig()
        if self.control == None:
            self.control = ControlConfig()


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
        managerCfg = ManagerConfig()
        for child in manager.childNodes:
            if child.nodeName in legalCommentSections:
                continue
            elif child.nodeName == u'hostCheck':
                managerCfg.loadHostCheck(child)
            elif child.nodeName == u'configCheck':
                managerCfg.loadConfigCheck(child)
            elif child.nodeName == u'heartbeat':
                managerCfg.loadHeartbeat(child)
        self.manager = managerCfg


    def loadControl(self, control):
        if control.hasAttribute('socket'):
            self.control = ControlConfig(control.getAttribute('socket'))


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
            elif c.nodeName in legalCommentSections:
                continue
            else:
                raise ConfigError, "unknown node '%s'"%c.nodeName
        serviceCfg.checkSanity()
        self.services[serviceName] = serviceCfg


    def toXML(self, padding=''):
        """

        """
        inner = u''
        indent=padding + '  '
        for service in self.getServices():
            inner += service.toXML(padding=indent)
        for cfgName in legalConfigSections:
            if hasattr(self, cfgName):
                inner += getattr(self, cfgName).toXML(padding=indent)
        data = {'tag': self.type, 'inner': inner}
        return '<%(tag)s>\n%(inner)s</%(tag)s>' % data

