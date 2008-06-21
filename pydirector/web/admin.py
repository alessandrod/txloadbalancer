import time
import urllib
import socket

from twisted.web import resource

from pydirector import Version
from pydirector.web import css
from pydirector.web import template

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
        return self.getPage(request)

class RunningPage(BasePage):
    """

    """
    def getPage(self, request):
        """
        This craziness is a modified version of the original.
        """
        refresh = False
        if request.args.has_key('refresh'):
            refresh = bool(request.args['refresh'][0])
        verbose = False
        resultMessage = ''
        content = self.getHeader(refreshURL='/running?refresh=1&ignore=%s' % time.time())
        if refresh:
            stopStart = template.stopRefresh % time.time()
        else:
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
                sch = self.parent.director.getScheduler(service.name, group.name)
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
        return str(content)

class RunningConfig(BasePage):
    """

    """

class StoredConfig(BasePage):
    """

    """

class DeleteHost(BasePage):
    """

    """

class AddHost(BasePage):
    """

    """

class AdminServer(resource.Resource):
    """

    """
    def __init__(self, director):
        resource.Resource.__init__(self)
        self.director = director
        self.config = director.conf.admin
        self.starttime = time.time()
        self.serverVersion = "pythondirector/%s"%Version

    def getChild(self, name, request):
        """

        """
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

    def render_GET(self, request):
        """

        """
        return "base"
