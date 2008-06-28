from twisted.internet import error
from twisted.internet import reactor
from twisted.internet import protocol

from txlb import logging



class TrackerMixin(object):
    """
    This is a simple class for setting the tracker attribute, something that is
    necessary when switching the active group.
    """
    def setTracker(self, groupName=''):
        if not groupName:
            group = self.director.getService(self.name).getEnabledGroup()
            groupName = group.name
        self.tracker = self.director.getTracker(self.name, groupName)
        if hasattr(self, 'factory'):
            self.factory.setTracker(groupName)



class Proxy(TrackerMixin):
    """
    Listener object. Listens at a given host/port for connections.
    Creates a receiver to collect data from client, and a sender to
    connect to the eventual destination host.

    Public API:

    method __init__(self, name, host, port, tracker, director)

    The 'name' attribute is actually the service name, and this is what
    provies the proxy manager the ability to look up a proxy in a service.

    attribute .tracker: read/write - a HostTracking object
    attribute .listening_address: read - a tuple of (host,port)
    """
    def __init__(self, name, host, port, director):
        self.name = name
        self.host = host
        self.port = int(port)
        self.listening_address = (self.host, self.port)
        self.director = director
        self.factory = ReceiverFactory(name, self.listening_address, director)
        self.setTracker()




class Sender(protocol.Protocol):
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
        The server is done, and has closed the connection. write out any
        remaining data, and close the socket.
        """
        if self.receiver is not None:
            if reason.type is error.ConnectionDone:
                pass
            elif reason.type is error.ConnectionLost:
                pass
            else:
                pass
            self.receiver.transport.loseConnection()


    def dataReceived(self, data):
        if self.receiver is None:
            logging.log("client got data, no receiver, tho\n")
        else:
            self.receiver.transport.write(data)


    def connectionMade(self):
        """
        We've connected to the destination server. tell the other end
        it's ok to send any buffered data from the client.
        """
        #XXX: OMG THIS IS HORRIBLE
        inSrc = self.receiver.transport.getPeer()
        outSrc = self.transport.getHost()
        self.receiver.factory.director.setClientAddress(
            (outSrc.host, outSrc.port),
            (inSrc.host, inSrc.port))
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



class SenderFactory(protocol.ClientFactory):
    """
    Create a Sender when needed. The sender connects to the remote host.
    """
    protocol = Sender
    noisy = 0


    def setReceiver(self, receiver):
        """
        This method is by the reveiver which instantiates this class to set
        its receiver, just after instantiation of this class.
        """
        self.receiver = receiver


    def buildProtocol(self, *args, **kw):
        """
        This method overrides the base class method, because we want to connect
        the objects together. Note that the setReseiver method that is called
        is from this factory's protocol, not from the factory itself.
        """
        protObj = protocol.ClientFactory.buildProtocol(self, *args, **kw)
        protObj.setReceiver(self.receiver)
        return protObj


    def clientConnectionFailed(self, connector, reason):
        """

        """
        # without overriding, this would hang up the inbound. We don't want
        # that
        self.receiver.factory.tracker.deadHost(self, reason)
        next = self.receiver.factory.tracker.getHost(
            self, self.receiver.client_addr)
        if next:
            logging.log("retrying with %s\n" % repr(next))
            host, port = next
            reactor.connectTCP(host, port, self)
        else:
            # No working servers!?
            logging.log("no working servers, manager -> aggressive\n")
            self.receiver.transport.loseConnection()


    def stopFactory(self):
        self.receiver.factory.tracker.doneHost(self)



class Receiver(protocol.Protocol):
    """
    Listener bit for clients connecting to the director.
    """
    sender = None
    buffer = ''
    receiverOk = 0


    def connectionMade(self):
        """
        This is invoked when a client connects to the director.
        """
        self.receiverOk = 1
        self.client_addr = self.transport.client
        sender = SenderFactory()
        sender.setReceiver(self)
        dest = self.factory.tracker.getHost(sender, self.client_addr)
        if dest:
            host, port = dest
            connection = reactor.connectTCP(host, port, sender)
            # XXX add optional support for logging these connections
        else:
            self.transport.loseConnection()


    def setSender(self, sender):
        """
        The sender side of the proxy is connected.
        """
        self.sender = sender
        if self.buffer:
            self.sender.transport.write(self.buffer)
            self.buffer = ''


    def connectionLost(self, reason):
        """
        The client has hung up/disconnected. Send the rest of the
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
            # setting up the proxy manager -> host connection. This then comes
            # in after this, and you end up with a hosed receiver that's
            # hanging around.
            # XXX probably want a test for this
            self.receiverOk = 0


    def getBuffer(self):
        """
        Return any buffered data.
        """
        return self.buffer


    def dataReceived(self, data):
        """
        Received data from the client. either send it on, or save it.
        """
        if self.sender is not None:
            self.sender.transport.write(data)
        else:
            self.buffer += data



class ReceiverFactory(TrackerMixin, protocol.ServerFactory):
    """
    Factory for the listener bit of the load balancer.
    """
    protocol = Receiver
    noisy = 0


    def __init__(self, name, (host, port), director):
        self.name = name
        self.host = host
        self.port = port
        # XXX self.tracker = tracker
        self.director = director

