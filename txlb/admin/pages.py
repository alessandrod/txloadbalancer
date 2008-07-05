import time
import urllib
import socket
from xml.dom import minidom

from twisted.web import http
from twisted.web import static
from twisted.web import resource

import txlb
from txlb import util
from txlb.admin import css
from txlb.admin import template


class UnauthorizedResource(resource.Resource):
    """
    The page resource to present when a restricted resource is requested, thus
    prompting the user with a basic auth dialog.
    """
    isLeaf = 1
    unauthorizedPage = static.Data(template.unauth, 'text/html')


    def render(self, request):
        request.setResponseCode(http.UNAUTHORIZED)
        request.setHeader(
            'WWW-authenticate', 'basic realm="PyDirector"')
        return self.unauthorizedPage.render(request)


class StyleSheet(resource.Resource):
    """
    The resource that serves the CSS.
    """
    def render_GET(self, request):
        """

        """
        return css.adminCSS


class BasePage(resource.Resource):
    """
    All resources that render the basic look and feel of the admin UI subclass
    this page class.
    """
    def __init__(self, parent):
        resource.Resource.__init__(self)
        self.parent = parent


    def getHeader(self, refreshURL='', msg=''):
        """

        """
        refresh = ''
        if refreshURL:
            refresh = template.refresh % (
                self.parent.conf.admin.refresh, refreshURL)
        if msg:
            msg = template.message % msg
        return template.header % (
            txlb.name, refresh, txlb.name, self.parent.serverVersion,
            socket.gethostname()) + msg


    def getBody(self):
        """
        Subclasses must override this.
        """
        raise NotImplemented


    def getFooter(self, message=''):
        """

        """
        if message:
            message = template.message % urllib.unquote(message)
        return template.footer % (txlb.projectURL, txlb.name, message)


    def getPage(self, request):
        """
        Subclasses must override this.
        """
        raise NotImplemented


    def render_GET(self, request):
        """

        """
        return str(self.getPage(request))


    def isReadOnly(self):
        """
        This check needs to be run before any form submission is processed.
        """
        if self.parent.director.isReadOnly:
            msg = "The load balancer is currently in read-only mode."
            request.redirect('/all?resultMessage=%s' % urllib.quote(msg))
            return True
        return False


class RunningPage(BasePage):
    """
    This class is responsible for presenting the admin UI, in all of it's data
    and button-pushing glory.
    """
    def getPage(self, request):
        """
        Don't look at me; this craziness is a modified version of the original.
        """
        verbose = False
        resultMessage = ''
        content = ''
        msg = ''
        if request.args.has_key('resultMessage'):
            msg = request.args['resultMessage'][0]
        if request.args.has_key('refresh'):
            refresh = bool(request.args['refresh'][0])
            url = '/all?refresh=1&ignore=%s' % time.time()
            content += self.getHeader(refreshURL=url, msg=msg)
            stopStart = template.stopRefresh % time.time()
        else:
            content += self.getHeader(msg=msg)
            stopStart = template.startRefresh % time.time()
        content += template.refreshButtons % (
            time.ctime(time.time()), time.time(), stopStart)
        for service in self.parent.conf.getServices():
            content += template.serviceName % service.name
            for index, l in enumerate(service.listen):
                proxy = self.parent.director.getProxy(service.name, index)
                hostPort = "%s:%s" % (proxy.host, proxy.port)
                content += template.listeningService % hostPort
            eg = service.getEnabledGroup()
            groups = service.getGroups()
            for group in groups:
                tracker = self.parent.director.getTracker(
                    service.name, group.name)
                stats = tracker.getStats()
                hdict = tracker.getHostNames()
                if group is eg:
                    klass = 'enabled'
                    desc = template.groupDescEnabled
                else:
                    klass = 'inactive'
                    desc = template.groupDescDisabled % (
                        service.name, group.name)
                content += template.groupName % (klass, group.name)
                content += desc
                content += template.groupHeaderForm % (
                    service.name, group.name, klass)
                counts = stats['openconns']
                failed = stats['failed']
                totals = stats['totals']
                k = counts.keys()
                k.sort()
                for h in k:
                    f = 0
                    if failed.has_key(h):
                        f = failed[h]
                    if counts.has_key(h):
                        oc = counts[h]
                    else:
                        oc = '--'
                    if totals.has_key(h):
                        tc = totals[h]
                    else:
                        tc = '--'
                    content += template.hostInfo % (
                        klass, hdict[h], h, oc, tc, f,
                        urllib.quote(service.name), urllib.quote(group.name),
                        urllib.quote(h))
                bad = stats['bad']
                if bad:
                    content += template.badHostGroup % klass
                for k in bad.keys():
                    host = '%s:%s' % k
                    when, what = bad[k]
                    content += template.badHostInfo % (
                        klass, hdict[host], host, what.getErrorMessage())
            content += template.serviceClose
        content += self.getFooter(resultMessage)
        return content


class RunningConfig(BasePage):
    """
    This class renders the in-memory configuration as XML.
    """
    def getPage(self, request):
        """

        """
        request.setHeader('Content-type', 'text/plain')
        return util.reprNestedObjects(self.parent.conf)


class StoredConfig(BasePage):
    """
    This page renders the on-disk XML configuration file.
    """
    def getPage(self, request):
        """

        """
        request.setHeader('Content-type', 'text/plain')
        return self.parent.conf.dom.toxml()


class DeleteHost(BasePage):
    """
    This page is responsible for removing a host from rotation in the admin UI.
    It also updates the tracker and pulls the host out of rotation there as
    well.
    """
    def getPage(self, request):
        """

        """
        request.setHeader('Content-type', 'text/html')
        if self.isReadOnly():
            return "OK"
        service = request.args['service'][0]
        group = request.args['group'][0]
        ip = request.args['ip'][0]
        tracker = self.parent.director.getTracker(
            serviceName=service, groupName=group)
        service = self.parent.conf.getService(service)
        eg = service.getEnabledGroup()
        if group == eg.name:
            if tracker.delHost(ip=ip, activegroup=1):
                msg = 'host %s deleted (from active group!)' % ip
            else:
                msg = 'host %s <b>not</b> deleted from active group' % ip
        else:
            if tracker.delHost(ip=ip):
                msg = 'host %s deleted from inactive group' % ip
            else:
                msg = 'host %s <b>not</b> deleted from inactive group' % ip
        request.redirect('/all?resultMessage=%s' % urllib.quote(msg))
        return "OK"


class AddHost(BasePage):
    """
    This page class is responsible for handling the "add page" action that puts
    new hosts into rotation, both in the admin UI as well as in the host
    tracking object.
    """
    def getPage(self, request):
        request.setHeader('Content-type', 'text/html')
        if self.isReadOnly():
            return "OK"
        serviceName = request.args['service'][0]
        groupName = request.args['group'][0]
        name = request.args['name'][0]
        ip = request.args['ip'][0]
        self.parent.editor.addHost(serviceName, groupName, name, ip)
        msg = 'Host %s(%s) added to %s / %s' % (
            name, ip, groupName, serviceName)
        request.redirect('/all?resultMessage=%s' % urllib.quote(msg))
        return "OK"


class EnableGroup(BasePage):
    """
    This page is responsible for enabling a different host group for a given
    service in the web UI.
    """
    def getPage(self, request):
        """

        """
        request.setHeader('Content-type', 'text/html')
        if self.isReadOnly():
            return "OK"
        serviceName = request.args['service'][0]
        newGroupName = request.args['group'][0]
        service = self.parent.director.getService(serviceName)
        oldGroupName = service.getEnabledGroup().name
        self.parent.editor.switchGroup(serviceName, oldGroupName, newGroupName)
        msg = "Group '%s' has been enabled." % newGroupName
        request.redirect('/all?resultMessage=%s' % urllib.quote(msg))
        return "OK"



def protect(method):
    """
    A decorator for use by Editor methods that need to support atomic-ish
    operations.
    """
    def decorator(self, *args, **kwds):
        self.begin()
        result = method(self, *args, **kwds)
        self.finish()
        return result
    return decorator



class Editor(object):
    """
    An object whose sole purpose is to collect all methods that change data
    into a single class. This is done in an effort to improve maintainability
    of data-changing code and to provide a unified, chohesive process whereby
    data edits are performed.
    """
    def __init__(self, conf, director):
        self.conf = conf
        self.director = director


    def begin(self):
        self.director.setReadOnly()
        print "Set to read-only mode."


    def finish(self):
        self.director.setReadWrite()
        print "Set to read-write mode."


    def addHost(self, serviceName, groupName, name, ip, weight=1):
        """
        This method adds a host to the tracker and model (director call) as
        well as the configuration data.
        """
        self.director.addHost(serviceName, groupName, name, ip, weight)
        group = self.conf.getService(serviceName).getGroup(groupName)
        group.addHost(name, ip, weight)
    addHost = protect(addHost)


    def delHost(self, serviceName, groupName, name, ip):
        """
        This method removes a host from the tracker and model (director call)
        as well as the configuration data.
        """
        self.director.delHost(serviceName, groupName, name, ip)
        group = self.conf.getService(serviceName).getGroup(groupName)
        group.delHost(name)
    delHost = protect(delHost)


    def switchGroup(self, serviceName, oldGroupName, newGroupName):
        """
        This method changes the current/active group for a given service.
        """
        # update the configuration info
        serviceConf = self.conf.getService(serviceName)
        serviceConf.setEnabledGroup(newGroupName)
        # update the tracker and model info
        self.director.switchGroup(serviceName, oldGroupName, newGroupName)
    switchGroup = protect(switchGroup)



class AdminServer(resource.Resource):
    """
    The admin server page is the root web object that publishes all the other
    resources.
    """
    def __init__(self, conf, director):
        resource.Resource.__init__(self)
        self.conf = conf
        self.director = director
        self.editor = Editor(conf, director)
        self.starttime = time.time()
        self.serverVersion = "%s/%s" % (txlb.shortName, txlb.version)

    def unauthorized(self):
        return UnauthorizedResource()

    def authenticateUser(self, request):
        # XXX this needs to be replaced with a guard/cred
        authstr = request.getHeader('Authorization')
        if not authstr:
            return False
        type, auth = authstr.split()
        if type.lower() != 'basic':
            return False
        auth = auth.decode('base64')
        user, pw = auth.split(':',1)
        userObj = self.conf.admin.getUser(user)
        if (userObj and userObj.checkPW(pw)):
            return True
        return False


    def getChild(self, name, request):
        """
        A simple object publisher that mapes part of a URL path to an object.
        """
        if not self.authenticateUser(request):
            return self.unauthorized()
        if name == 'all' or name == '':
            page = RunningPage(self)
            return page
        elif name == 'txlb.css':
            return StyleSheet()
        elif name == 'config.obj':
            return RunningConfig(self)
        elif name == 'config.xml':
            return StoredConfig(self)
        elif name == 'delHost':
            return DeleteHost(self)
        elif name == 'addHost':
            return AddHost(self)
        elif name == 'enableGroup':
            return EnableGroup(self)
        return resource.Resource.getChild(self, name, request)


