#
# Copyright (c) 2002-2004 ekit.com Inc (http://www.ekit-inc.com)
# and Anthony Baxter <anthony@interlink.com.au>
#
# Networking core - twisted version (http://www.twistedmatrix.com)
#
# $Id: pdnetworktwisted.py,v 1.11 2004/12/14 13:31:39 anthonybaxter Exp $
#

from twisted.internet.protocol import ServerFactory, ClientFactory, Protocol
from twisted.internet import reactor
import twisted.internet

import pdlogging



class Listener:
    """
        Listener object. Listens at a given host/port for connections.
        Creates a receiver to collect data from client, and a sender to
        connect to the eventual destination host.

        Public API:

        method __init__(self, name, (bindhost, bindport), scheduler)
        attribute .scheduler: read/write - a PDScheduler
        attribute .listening_address: read - a tuple of (host,port)
    """

    def __init__(self, name, (bindhost, bindport), scheduler):
        self.name = name
        self.listening_address = (bindhost, bindport)
        self.rfactory = ReceiverFactory((bindhost,bindport), scheduler)
        self.setScheduler(scheduler)
        reactor.listenTCP(bindport, self.rfactory, interface=bindhost)

    def setScheduler(self, scheduler):
        self.scheduler = scheduler
        self.rfactory.setScheduler(scheduler)

class Sender(Protocol):
    """
        A Sender object connects to the remote final server, and passes data
        back and forth. Unlike the receiver, it's not necessary to buffer up
        data, since the client _must_ be connected (if it's not, toss the
        data)
    """
    receiver = None

    def setReceiver(self, receiver):
        self.receiver = receiver

    def connectionLost(self, reason):
        """
            the server is done, and has closed the connection. write out any
            remaining data, and close the socket.
        """
        if self.receiver is not None:
            if reason.type is twisted.internet.error.ConnectionDone:
                return
            elif reason.type is twisted.internet.error.ConnectionLost:
                pass
            else:
                #print id(self),"connection to server lost:",reason
                pass
            self.receiver.transport.loseConnection()

    def dataReceived(self, data):
        #print "client data", len(data)
        if self.receiver is None:
            pdlogging.log("client got data, no receiver, tho\n", datestamp=1)
        else:
            self.receiver.transport.write(data)

    def connectionMade(self):
        """
            we've connected to the destination server. tell the other end
            it's ok to send any buffered data from the client.
        """
        #print "client connection",self.factory
        if self.receiver.receiverOk:
            self.receiver.setSender(self)
        else:
            # the receiver's already given up at this point and gone
            # home. _if_ the receiver got data from the client, we
            # must send it on - the client thinks that it's successfully
            # sent it, so we should honour that. We don't need to worry
            # about the response from the server itself.
            data = self.receiver.getBuffer()
            if data:
                self.transport.write(data)
            self.transport.loseConnection()
            self.setReceiver(None)

class SenderFactory(ClientFactory):
    "create a Sender when needed. The sender connects to the remote host"
    protocol = Sender
    noisy = 0

    def setReceiver(self, receiver):
        #print "senderfactory.setreceiver", receiver
        self.receiver = receiver

    def buildProtocol(self, *args, **kw):
        # over-ride the base class method, because we want to connect
        # the objects together.
        protObj = ClientFactory.buildProtocol(self, *args, **kw)
        protObj.setReceiver(self.receiver)
        return protObj

    def clientConnectionFailed(self, connector, reason):
        #print "bzzt. we failed,", connector, reason

        # this would hang up the inbound. We don't want that.
        #self.receiver.transport.loseConnection()
        self.receiver.factory.scheduler.deadHost(self, reason)
        next =  self.receiver.factory.scheduler.getHost(self,
                                                    self.receiver.client_addr)
        if next:
            pdlogging.log("retrying with %s\n"%repr(next), datestamp=1)
            host, port = next
            reactor.connectTCP(host, port, self)
        else:
            # No working servers!?
            pdlogging.log("no working servers, manager -> aggressive\n",
                          datestamp=1)
            self.receiver.transport.loseConnection()

    def stopFactory(self):
        self.receiver.factory.scheduler.doneHost(self)

class Receiver(Protocol):
    "Listener bit for clients connecting to the director"

    sender = None
    buffer = ''
    receiverOk = 0

    def connectionMade(self):
        "This is invoked when a client connects to the director"
        self.receiverOk = 1
        self.client_addr = self.transport.client
        sender = SenderFactory()
        sender.setReceiver(self)
        dest = self.factory.scheduler.getHost(sender, self.client_addr)
        if dest:
            host, port = dest
            sender = reactor.connectTCP(host, port, sender)
        else:
            #print "(still) no working servers!"
            self.transport.loseConnection()

    def setSender(self, sender):
        "the sender side of the proxy is connected"
        self.sender = sender
        if self.buffer:
            self.sender.transport.write(self.buffer)
            self.buffer = ''

    def connectionLost(self, reason):
        """
            the client has hung up/disconnected. send the rest of the
            data through before disconnecting. Let the client know that
            it can just discard the data.
        """
        # damn. XXX TODO. If the client connects, sends, then disconnects,
        # before the end server has connected, we have data loss - the client
        # thinks it's connected and sent the data, but it won't have. damn.
        if self.sender:
            # according to the interface docstring, this sends all pending
            # data before closing the connection.
            self.sender.setReceiver(None)
            self.sender.transport.loseConnection()
            self.receiverOk = 0
        else:
            # there's a race condition here - we could be in the process of
            # setting up the director->server connection. This then comes in
            # after this, and you end up with a hosed receiver that's hanging
            # around.
            self.receiverOk = 0

    def getBuffer(self):
        "return any buffered data"
        return self.buffer

    def dataReceived(self, data):
        "received data from the client. either send it on, or save it"
        if self.sender is not None:
            self.sender.transport.write(data)
        else:
            self.buffer += data


class ReceiverFactory(ServerFactory):
    "Factory for the listener bit of the pydirector"
    protocol = Receiver
    noisy = 0

    def __init__(self, (bindhost, bindport), scheduler):
        self.bindhost = bindhost
        self.bindport = bindport
        self.scheduler = scheduler

    def setScheduler(self, scheduler):
        self.scheduler = scheduler


def mainloop(timeout=5):
    " run the main loop "
    #print "running mainloop"
    reactor.run()
