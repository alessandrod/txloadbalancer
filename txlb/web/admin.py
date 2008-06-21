import time
import urllib
import socket
from xml.dom import minidom

from twisted.web import http
from twisted.web import static
from twisted.web import resource

from txlb import Version
from txlb.web import css
from txlb.web import template

class UnauthorizedResource(resource.Resource):
    isLeaf = 1
    unauthorizedPage = static.Data(template.unauth, 'text/html')

    def render(self, request):
        request.setResponseCode(http.UNAUTHORIZED)
        request.setHeader(
            'WWW-authenticate', 'basic realm="PyDirector"')
        return self.unauthorizedPage.render(request)

class StyleSheet(resource.Resource):
    """

    """
    def render_GET(self, request):
        """

        """
        return css.adminCSS

class BasePage(resource.Resource):
    """

    """
    def __init__(self, parent):
        resource.Resource.__init__(self)
        self.parent = parent

    def getHeader(self, refreshURL=''):
        """

        """
        refresh = ''
        if refreshURL:
            # XXX add an admin configuration option for setting the refresh
            # rate
            refreshRate = 30
            refresh = template.refresh % (refreshRate, refreshURL)
        return template.header % (
            refresh, self.parent.serverVersion, socket.gethostname())

    def getBody(self):
        """
        Subclasses must override this.
        """
        raise NotImplemented

    def getFooter(self, message=''):
        """

        """
        # XXX put the project URL in the admin config
        projectURL ='http://pythondirector.sf.net'
        if message:
            message = template.message % urllib.unquote(message)
        return template.footer % (projectURL, message)


    def getPage(self):
        """
        Subclasses must override this.
        """
        raise NotImplemented

    def render_GET(self, request):
        """

        """
        return str(self.getPage(request))

class RunningPage(BasePage):
    """

    """
    def getPage(self, request):
        """
        Don't look at me; this craziness is a modified version of the original.
        """
        verbose = False
        resultMessage = ''
        content = ''
        if request.args.has_key('refresh'):
            refresh = bool(request.args['refresh'][0])
            url = '/running?refresh=1&ignore=%s' % time.time()
            content += self.getHeader(refreshURL=url)
            stopStart = template.stopRefresh % time.time()
        else:
            content += self.getHeader()
            stopStart = template.startRefresh % time.time()
        content += template.refreshButtons % (
            time.ctime(time.time()), time.time(), stopStart)
        for service in self.parent.director.conf.getServices():
            content += template.serviceName % service.name
            for l in service.listen:
                content += template.listeningService % l
            eg = service.getEnabledGroup()
            groups = service.getGroups()
            for group in groups:
                sch = self.parent.director.getScheduler(
                    service.name, group.name)
                stats = sch.getStats(verbose=verbose)
                hdict = sch.getHostNames()
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
                counts = stats['open']
                totals = stats['totals']
                k = counts.keys()
                k.sort()
                for h in k:
                    if counts.has_key(h):
                        oc = counts[h]
                    else:
                        oc = '--'
                    if totals.has_key(h):
                        tc = totals[h]
                    else:
                        tc = '--'
                    content += template.hostInfo % (
                        klass, hdict[h], h, oc, tc, urllib.quote(service.name),
                        urllib.quote(group.name), urllib.quote(h))
                bad = stats['bad']
                if bad:
                    content += template.badHostGroup % klass
                for k in bad.keys():
                    host = '%s:%s' % k
                    when, what = bad[k]
                    content += template.badHostInfo % (
                        klass, hdict[host], host, what)
            content += template.serviceClose
        content += self.getFooter(resultMessage)
        return content

class RunningConfig(BasePage):
    """

    """
    def getPage(self, request):
        """

        """
        request.setHeader('Content-type', 'text/plain')
        verbose = False
        conf = self.parent.director.conf
        doc = minidom.Document()
        top = doc.createElement("pdconfig")
        doc.appendChild(top)
        for service in conf.getServices():
            top.appendChild(doc.createTextNode("\n    "))
            serv = doc.createElement("service")
            serv.setAttribute('name', service.name)
            top.appendChild(serv)
            for l in service.listen:
                serv.appendChild(doc.createTextNode("\n        "))
                lobj = doc.createElement("listen")
                lobj.setAttribute('ip', l)
                serv.appendChild(lobj)
            groups = service.getGroups()
            for group in groups:
                serv.appendChild(doc.createTextNode("\n        "))
                sch = self.parent.director.getScheduler(service.name, group.name)
                xg = doc.createElement("group")
                xg.setAttribute('name', group.name)
                xg.setAttribute('scheduler', sch.schedulerName)
                serv.appendChild(xg)
                stats = sch.getStats(verbose=verbose)
                hosts = group.getHosts()
                hdict = sch.getHostNames()
                counts = stats['open']
                ahosts = counts.keys() # ahosts is now a list of active hosts
                # now add disabled hosts.
                for k in stats['bad'].keys():
                    ahosts.append('%s:%s'%k)
                ahosts.sort()
                for h in ahosts:
                    xg.appendChild(doc.createTextNode("\n            "))
                    xh = doc.createElement("host")
                    xh.setAttribute('name', hdict[h])
                    xh.setAttribute('ip', h)
                    xg.appendChild(xh)
                xg.appendChild(doc.createTextNode("\n        "))
            serv.appendChild(doc.createTextNode("\n        "))
            eg = service.getEnabledGroup()
            xeg = doc.createElement("enable")
            xeg.setAttribute("group", eg.name)
            serv.appendChild(xeg)
            serv.appendChild(doc.createTextNode("\n    "))
        top.appendChild(doc.createTextNode("\n    "))
        # now the admin block
        admin = self.parent.director.conf.admin
        if admin is not None:
            xa = doc.createElement("admin")
            xa.setAttribute("listen", "%s:%s"%admin.listen)
            top.appendChild(xa)
            for user in admin.getUsers():
                xa.appendChild(doc.createTextNode("\n        "))
                xu = doc.createElement("user")
                xu.setAttribute("name", user.name)
                xu.setAttribute("password", user.password)
                xu.setAttribute("access", user.access)
                xa.appendChild(xu)
            xa.appendChild(doc.createTextNode("\n    "))
            top.appendChild(doc.createTextNode("\n    "))
        # finally, the logging section (if set)
        #if logger.logfile is not None:
        #    xl = doc.createElement("logging")
        #    xl.setAttribute("file", logger.logfile)
        #    top.appendChild(xl)
        # final newline
        top.appendChild(doc.createTextNode("\n"))
        # and spit out the XML
        return doc.toxml()

class StoredConfig(BasePage):
    """

    """
    def getPage(self, request):
        """

        """
        request.setHeader('Content-type', 'text/plain')
        return self.parent.director.conf.dom.toxml()

class DeleteHost(BasePage):
    """

    """
    def getPage(self, request):
        """

        """
        service = request.args['service'][0]
        group = request.args['group'][0]
        ip = request.args['ip'][0]
        sched = self.parent.director.getScheduler(
            serviceName=service, groupName=group)
        service = self.parent.director.conf.getService(service)
        eg = service.getEnabledGroup()
        if group == eg.name:
            if sched.delHost(ip=ip, activegroup=1):
                msg = 'host %s deleted (from active group!)' % ip
            else:
                msg = 'host %s <b>not</b> deleted from active group' % ip
        else:
            if sched.delHost(ip=ip):
                msg = 'host %s deleted from inactive group' % ip
            else:
                msg = 'host %s <b>not</b> deleted from inactive group' % ip
        request.redirect('/running?resultMessage=%s' % urllib.quote(msg))
        return "OK"

class AddHost(BasePage):
    """

    """
    def getPage(self, request):
        """

        """
        service = request.args['service'][0]
        group = request.args['group'][0]
        name = request.args['name'][0]
        ip = request.args['ip'][0]
        sched = self.parent.director.getScheduler(
            serviceName=service, groupName=group)
        sched.newHost(name=name, ip=ip)
        # also add to conf DOM object
        msg = 'Host %s(%s) added to %s / %s' % (name, ip, group, service)
        request.redirect('/running?resultMessage=%s' % urllib.quote(msg))
        return "OK"

class AdminServer(resource.Resource):
    """

    """
    def __init__(self, director):
        resource.Resource.__init__(self)
        self.director = director
        self.config = director.conf.admin
        self.starttime = time.time()
        self.serverVersion = "pythondirector/%s" % Version

    def unauthorized(self):
        return UnauthorizedResource()

    def authenticateUser(self, request):
        authstr = request.getHeader('Authorization')
        if not authstr:
            return False
        type, auth = authstr.split()
        if type.lower() != 'basic':
            return False
        auth = auth.decode('base64')
        user, pw = auth.split(':',1)
        userObj = self.config.getUser(user)
        if (userObj and userObj.checkPW(pw)):
            return True
        return False

    def getChild(self, name, request):
        """

        """
        if not self.authenticateUser(request):
            return self.unauthorized()
        if name == 'running' or name == '':
            return RunningPage(self)
        elif name == 'pydirector.css':
            return StyleSheet()
        elif name == 'running.xml':
            return RunningConfig(self)
        elif name == 'config.xml':
            return StoredConfig(self)
        elif name == 'delHost':
            return DeleteHost(self)
        elif name == 'addHost':
            return AddHost(self)
        return resource.Resource.getChild(self, name, request)


