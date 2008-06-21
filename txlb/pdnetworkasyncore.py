#
# Copyright (c) 2002-2004 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# Networking core - asyncore version
#
# $Id: pdnetworkasyncore.py,v 1.6 2004/12/14 13:31:39 anthonybaxter Exp $
#

import asyncore, asynchat, socket, sys, errno

import pdlogging

#asyncore.DEBUG = 1

class Listener(asyncore.dispatcher):
    """ This object sits and waits for incoming connections
        on a port. When it receives a connection, it creates
        a Receiver to accept data to the port, and also passes
        the scheduler across to the Receiver."""

    def __init__(self, name, (bindhost, bindport), scheduler):
        asyncore.dispatcher.__init__(self)
        self.scheduler = scheduler
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.listening_address =(bindhost,bindport)
        self.name = name
        self.bind((bindhost,bindport))
        self.listen(10)

    def setScheduler(self, scheduler):
        self.scheduler = scheduler

    def handle_accept(self):
        # don't accept if no backends available!
        who = self.accept()
        #print "got connection from", who
        try:
            # it's critical that the listener is not killed by
            # exceptions from the Receivers or Senders
            r = Receiver(self, who, self.scheduler)
            r.go()
        except:
            nil, t, v, tbinfo = pdlogging.compact_traceback()
            pdlogging.log('Listener: %s %s %s\n'%
                            (str(t), str(v), str(tbinfo)), datestamp=1)

class Receiver(asynchat.async_chat):
    """ A Receiver is created when a new inbound connection
        from a client is detected. It sets itself up to get
        the client data, then creates a Sender object to handle
        the server side of the connection. It passes the
        Scheduler across to the Sender - this is called to
        ask which end server to use """

    def __init__(self, listener, (conn, addr), scheduler):
        asynchat.async_chat.__init__(self, conn)
        self.set_terminator(None)
        self.listener = listener
        self.id = id(self)
        self.client_addr = addr
        self.sender = Sender(self, scheduler)
        self.sender.id = self.id
        self.scheduler = scheduler
        self.buffer = ''
        self.serverOk = 0
        self.cacheBuffer = ''
        #print "receiver %x init"%id(self)

    def go(self):
        self.sender.go()

    def retry_connection(self):
        self.sender = Sender(self, self.scheduler)
        self.sender.id = self.id
        self.buffer = self.cacheBuffer
        self.cacheBuffer = ''
        self.maybe_push_data()

    def collect_incoming_data(self, data):
        self.buffer = self.buffer + data
        self.maybe_push_data()

    def maybe_push_data(self, force=0):
        if self.buffer:
            data = self.buffer
            self.buffer = ''
            self.sender.push(data)
            # if this server's known to be answering...
            if self.serverOk:
                self.cacheBuffer = ''
            else:
                self.cacheBuffer += data

    def handle_close(self):
        """the connection to the client is done. no point in the sender
        continuing, as the client connection's toast"""
        #print "receiver %x/sender %x close"%(id(self), id(self.sender))
        self.maybe_push_data(force=1)
        try:
            # There's a race condition here, sometimes we lose. but we
            # don't actually care.
            self.sender.close()
            self.scheduler.doneHost(self)
        except:
            pass
        self.close()

class Sender(asynchat.async_chat):
    """A sender handles the proxy<->server side of the
       conversation. When created, it gets passed a Scheduler
       object. It asks the scheduler object to find out the
       eventual host to connect."""

    def __init__(self, receiver, scheduler):
        asynchat.async_chat.__init__(self)
        self.receiver = receiver
        self.set_terminator(None)
        self.scheduler = scheduler
        self.buffer = ''

    def go(self):
        self.do_connect()

    def do_connect(self):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        dest = self.scheduler.getHost(self.receiver, self.receiver.client_addr)
        if dest:
            self.dest = dest
            try:
                self.connect(self.dest)
            except:
                self.handle_error()
        else:
            self.log_info("NO WORKING HOSTS!\n", 'fatal')
            self.close()

    def handle_connect(self):
        pass

    def dead_server(self, retry=0, reason=""):
        # The server we connected to is dead. Let the scheduler know,
        # then, if required, get the receiver to retry the connection.
        # (this will get a new Sender instance, connected to a new dest.
        print "marking server %s as dead (%s)"%(self.dest, reason)
        self.scheduler.deadHost(self.receiver, reason)
        if retry:
            r = self.receiver
            del self.receiver
            r.retry_connection()
            self.close()

    def handle_error (self):
        e,v,t = sys.exc_info()
        what = ''
        if e is socket.error:
            if v[0] == errno.ECONNREFUSED:
                # server is down :(
                self.dead_server(retry=1, reason="conn_refused")
                return
            elif v[0] == errno.ECONNABORTED:
                self.close()
                return
            else:
                what = " (%s)"%errno.errorcode[v[0]]
        elif hasattr(socket, 'gaierror') and e is socket.gaierror:
            if v[0] == -2:
                self.dead_server(retry=1, reason="unknown_name")
                return
        nil, t, v, tbinfo = pdlogging.compact_traceback()
        # sometimes user repr method will crash.
        try:
            self_repr = repr (self)
        except:
            self_repr = '<__repr__ (self) failed for object at %0x>' % id(self)
        self.log_info (
            'sender python exception, closing channel %s (%s:%s%s %s)' % (
                self_repr,
                t,
                v, what,
                tbinfo
                ),
            'error'
            )
        self.close()

    def collect_incoming_data(self, data):
        self.receiver.push(data)

    def handle_close(self):
        #print "receiver %x close_when_done"%id(self.receiver)
        self.receiver.close_when_done()
        self.scheduler.doneHost(self.receiver)
        self.close()

    def log(self, message):
        pdlogging.log(message)

    def log_info (self, message, type='info'):
        pdlogging.log('%s: %s\n' % (type, message), datestamp=1)

def mainloop(timeout):
    " wrapper around the I/O library's main loop "
    asyncore.loop(timeout = 4)
