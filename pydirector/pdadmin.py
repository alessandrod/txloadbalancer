#
# Copyright (c) 2002-2004 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# $Id: pdadmin.py,v 1.16 2004/12/14 13:31:39 anthonybaxter Exp $
#

import sys
if sys.version_info < (2,2):
    class object: pass
import urllib
import threading, BaseHTTPServer, SocketServer, urlparse, re, urllib
import socket, time, sys, traceback, time
from xml.dom.minidom import Document

from pydirector import micropubl
from pydirector import Version, pdlogging
from pydirector.web import css
from pydirector.web import template

try:
    from M2Crypto import SSL
    from M2Crypto.SSL import ThreadingSSLServer
    from M2Crypto import Rand
except ImportError:
    ThreadingSSLServer = object


def dictify(q):
    """
    takes string of form '?a=b&c=d&e=f'
    and returns {'a':'b', 'c':'d', 'e':'f'}
    """
    out = {}
    if not q: return {}
    avs = q.split('&')
    for av in avs:
        #print "av", av
        a,v = av.split('=',1)
        out[urllib.unquote(a)] = urllib.unquote(v)
    return out


def html_quote(str):
    return re.subn("<", "&lt;", str)[0]


def get_ssl_context():
    Rand.load_file('randpool.dat', -1)
    ctx = init_context('sslv23', 'server.pem', 'ca.pem',
        SSL.verify_none)
        #SSL.verify_peer | SSL.verify_fail_if_no_peer_cert)
    ctx.set_tmp_dh('dh1024.pem')
    Rand.save_file('randpool.dat')
    return ctx


def init_context(protocol, certfile, cafile, verify, verify_depth=10):
    ctx=SSL.Context(protocol)
    ctx.load_cert(certfile)
    ctx.load_client_ca(cafile)
    ctx.load_verify_info(cafile)
    ctx.set_verify(verify, verify_depth)
    ctx.set_allow_unknown_ca(1)
    ctx.set_session_id_ctx('https_srv')
    ctx.set_info_callback()
    return ctx


class PDTCPServerBase:
    allow_reuse_address = 1
    def handle_error(self, request, client_address):
        "overridden from SocketServer.BaseServer"
        nil, t, v, tbinfo = pdlogging.compact_traceback()
        pdlogging.log("ADMIN(Exception) %s - %s: %s %s\n"%
                (time.ctime(time.time()), t,v,tbinfo))

class PDTCPServer(SocketServer.ThreadingTCPServer, PDTCPServerBase):
    allow_reuse_address = 1

class PDTCPServerSSL(ThreadingSSLServer, PDTCPServerBase):
    allow_reuse_address = 1
    def __init__(self, server_addr, handler, ssl_ctx):
        SSL.ThreadingSSLServer.__init__(self, server_addr, handler, ssl_ctx)
        self.server_name = server_addr[0]
        self.server_port = server_addr[1]

    def finish(self):
        self.request.set_shutdown(SSL.SSL_RECEIVED_SHUTDOWN |
                                  SSL.SSL_SENT_SHUTDOWN)
        self.request.close()


class AdminClass(BaseHTTPServer.BaseHTTPRequestHandler,
                 micropubl.MicroPublisher):
    server_version = "pythondirector/%s"%Version
    director = None
    config = None
    starttime = None
    published_prefix = "pdadmin_"

    def getUser(self, authstr):
        type,auth = authstr.split()
        if type.lower() != 'basic':
            return None
        auth = auth.decode('base64')
        user,pw = auth.split(':',1)
        userObj = self.config.getUser(user)
        if not ( userObj and userObj.checkPW(pw) ):
            # unknown user or incorrect pw
            return None
        else:
            return userObj

    def unauth(self, why):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'basic realm="python director"')
        self.wfile.write("<p>Unauthorised</p>\n")

    def header(self, html=1, refreshURL=''):
        self.send_response(200)
        if html:
            self.send_header("Content-type", "text/html")
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        if html:
            refresh = ''
            if refreshURL:
                # XXX add an admin configuration option for setting the refresh
                # rate
                refreshRate = 30
                refresh = template.refresh % (refreshRate, refreshURL)
            data = template.header % (
                refresh, self.server_version, socket.gethostname())
            self.wfile.write(data)

    def footer(self, message=''):
        # XXX put the project URL in the admin config
        projectURL ='http://pythondirector.sf.net'
        if message:
            message = template.message % urllib.unquote(message)
        data = template.footer % (projectURL, message)
        self.wfile.write(data)

    def redir(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def action_done(self, mesg):
        self.redir('/running?resultMessage=%s' % urllib.quote(mesg))

    def do_GET(self):
        try:
            self.do_request()
        except:
            self.log_exception()

    def do_request(self):
        h,p,u,p,q,f = urlparse.urlparse(self.path)

        authstr = self.headers.get('Authorization','')
        if authstr:
            user = self.getUser(authstr)
        if not (authstr and user):
            self.unauth(why='no valid auth')
            return

        if u == "/":
            u = 'index_html'

        args = dictify(q)

        if u.startswith("/"):
            u = u[1:]
        u = re.sub(r'\.', '_', u)

        try:
            self.publish(u, args, user=user)
        except micropubl.NotFoundError:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html><body>no such URL</body></html>")
        except micropubl.AccessDenied:
            self.unauth('insufficient privileges')
            return
        except micropubl.uPublisherError:
            self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html><body><h2>error:</h2>")
            e,v,t = sys.exc_info()
            self.wfile.write("<b>%s %s</b>\n<pre>"%(e,v))
            self.wfile.write("\n".join(traceback.format_tb(t)))
            self.wfile.write("</pre>\n</body></html>")

    def pdadmin_pydirector_css(self, Access='Read'):
        self.header(html=0)
        self.wfile.write(css.adminCSS)

    def pdadmin_index_html(self, Access='Read'):
        self.header(html=1)
        self.wfile.write("""
            <p>Python Director version %s, running on %s</p>
            <p>Running since %s</p>
            """%(self.server_version,
                 socket.gethostname(),
                 time.ctime(self.starttime)))
        self.footer()

    def pdadmin_running_xml(self, verbose=0, Access='Read'):
        self.header(html=0)
        W = self.wfile.write
        conf = self.director.conf
        doc = Document()
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
                sch = self.director.getScheduler(service.name, group.name)
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
        admin = self.director.conf.admin
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
        logger = pdlogging.Logger
        if logger.logfile is not None:
            xl = doc.createElement("logging")
            xl.setAttribute("file", logger.logfile)
            top.appendChild(xl)
        # final newline
        top.appendChild(doc.createTextNode("\n"))
        # and spit out the XML
        self.wfile.write(doc.toxml())


    def pdadmin_running_txt(self, verbose=0, Access='Read'):
        self.header(html=0)
        W = self.wfile.write
        conf = self.director.conf
        for service in conf.getServices():
            eg = service.getEnabledGroup()
            for l in service.listen:
                W('service %s %s %s\n'%(service.name, l, eg.name))
            groups = service.getGroups()
            for group in groups:
                sch = self.director.getScheduler(service.name, group.name)
                stats = sch.getStats(verbose=verbose)
                hosts = group.getHosts()
                hdict = sch.getHostNames()
                if group is eg:
                    klass = 'enabled'
                else:
                    klass = 'inactive'
                W('group %s %s\n'%(group.name, klass))
                counts = stats['open']
                k = counts.keys()
                k.sort() # k is now a list of hosts in the opencount stats
                for h in k:
                    W("host %s %s "%(hdict[h], h))
                    if counts.has_key(h):
                        W("%s -\n"%counts[h])
                    else:
                        W("- -\n")
                bad = stats['bad']
                for k in bad:
                    host = '%s:%s'%k
                    W("disabled %s %s"%(hdict[host], host))
                    when,what = bad[k]
                    W(" %s -\n"%what)

    def pdadmin_running(self, verbose=0, refresh=0, ignore='', resultmessage='', Access='Read'):
        self.header(html=1, refreshURL='/running?refresh=1&ignore=%s' % time.time())
        W = self.wfile.write
        if refresh:
            stopStart = template.stopRefresh % time.time()
        else:
            stopStart = template.startRefresh % time.time()
        W(template.refreshButtons % (
            time.ctime(time.time()), time.time(), stopStart))
        conf = self.director.conf
        for service in conf.getServices():
            W(template.serviceName % service.name)
            for l in service.listen:
                W(template.listeningService % l)
            eg = service.getEnabledGroup()
            groups = service.getGroups()
            for group in groups:
                sch = self.director.getScheduler(service.name, group.name)
                stats = sch.getStats(verbose=verbose)
                hdict = sch.getHostNames()
                if group is eg:
                    klass = 'enabled'
                    desc = template.groupDescEnabled
                else:
                    klass = 'inactive'
                    desc = template.groupDescDisabled % (
                        service.name, group.name)
                W(template.groupName % (klass, group.name))
                W(desc)
                W(template.groupHeaderForm % (
                    service.name, group.name, klass))
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
                    W(template.hostInfo % (
                        klass, hdict[h], h, oc, tc, urllib.quote(service.name),
                        urllib.quote(group.name), urllib.quote(h)))
                bad = stats['bad']
                if bad:
                    W(template.badHostGroup % klass)
                for k in bad.keys():
                    host = '%s:%s' % k
                    when, what = bad[k]
                    W(template.badHostInfo % (klass, hdict[host], host, what))
            W(template.serviceClose)
        self.footer(resultmessage)

    def pdadmin_addHost(self, service, group, name, ip, Access='Write'):
        sched = self.director.getScheduler(serviceName=service, groupName=group)
        sched.newHost(name=name, ip=ip)
        # also add to conf DOM object
        self.action_done('Host %s(%s) added to %s / %s'%(
                name, ip, group, service))
        self.wfile.write("OK\n")

    def pdadmin_delHost(self, service, group, ip, Access='Write'):
        sched = self.director.getScheduler(serviceName=service, groupName=group)
        service = self.director.conf.getService(service)
        eg = service.getEnabledGroup()
        if group == eg.name:
            if sched.delHost(ip=ip, activegroup=1):
                self.action_done('host %s deleted (from active group!)'%ip)
            else:
                self.action_done('host %s <b>not</b> deleted from active group'%ip)
        else:
            if sched.delHost(ip=ip):
                self.action_done('host %s deleted from inactive group'%ip)
            else:
                self.action_done('host %s <b>not</b> deleted from inactive group'%ip)
        self.wfile.write("OK\n")

    def pdadmin_delAllHosts(self, service, group, Access='Write'):
        self.action_done('not implemented yet')
        self.wfile.write("OK\n")

    def pdadmin_enableGroup(self, service, group, Access='Write'):
        self.director.enableGroup(service, group)
        self.action_done('Group %s enabled for service %s'%(
                group, service))
        self.wfile.write("OK\n")

    def pdadmin_changeScheduler(self, service, group, scheduler, Access='Write'):
        self.action_done('not implemented yet')
        self.wfile.write("OK\n")

    def pdadmin_config_xml(self, Access='Read'):
        self.header(html=0)
        self.wfile.write(self.director.conf.dom.toxml())

    def pdadmin_status_txt(self, verbose=0, Access='Read'):
        self.header(html=0)
        W = self.wfile.write
        # needs to handle multiple listeners per service!
        raise "Broken", "update me!"
        for listener in self.director.listeners.values():
            sch_stats = listener.scheduler.getStats(verbose='verbose')
            lh,lp = listener.listening_address
            sn = listener.scheduler.schedulerName
            W("service: %s\n"%listener.name)
            W("listen: %s:%s %s\n"%(lh,lp, sn))
            for h, c in sch_stats['open']:
                W("host: %s:%s %s\n"%(h[0],h[1],c))
            bad = sch_stats['bad']
            if bad:
                for b in bad:
                    W("disabled: %s:%s\n"%b)

    def pdadmin_addUser(self, name, password, access, Access='Write'):
        if self.adminconf.getUser(name):
            self.action_done('user %s already exists'%name)
            self.wfile.write("NOT OK\n")
        else:
            self.adminconf.addUser(name, password, access)
            self.action_done('user %s added'%name)
            self.wfile.write("OK\n")

    def pdadmin_delUser(self, name, Access='Write'):
        if self.adminconf.getUser(name):
            self.adminconf.delUser(name)
            self.action_done('user %s deleted'%name)
            self.wfile.write("OK\n")
        else:
            self.action_done('user %s not found'%name)
            self.wfile.write("NOT OK\n")

    def pdadmin_unimplemented(self, Access='Write'):
        self.action_done('not implemented yet')
        self.wfile.write("OK\n")

    def log_message(self, format, *args):
        "overridden from BaseHTTPServer"
        pdlogging.log("ADMIN: %s - - [%s] %s\n" %
                     (self.address_string(),
                      self.log_date_time_string(),
                      format%args))

    def log_exception(self):
        nil, t, v, tbinfo = pdlogging.compact_traceback()
        pdlogging.log("ADMIN(Exception) %s - %s: %s %s\n"%
                (time.ctime(time.time()), t,v,tbinfo))


def start(adminconf, director):
    AdminClass.director = director
    AdminClass.config = adminconf
    AdminClass.starttime = time.time()
    if adminconf.secure == 'yes' and SSL is not None:
        tcps = PDTCPServerSSL(adminconf.listen, AdminClass, get_ssl_context())
    else:
        tcps = PDTCPServer(adminconf.listen, AdminClass)
    at = threading.Thread(target=tcps.serve_forever)
    at.setDaemon(1)
    at.start()

