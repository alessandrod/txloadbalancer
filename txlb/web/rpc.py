import inspect

from twisted.web import xmlrpc
from twisted.web import resource

try:
    from txjsonrpc.web import jsonrpc
except ImportError:
    from txlb.util import dummyModule as jsonrpc

from txlb.web import rest
from txlb.api import data
from txlb.api.base import BaseAPI


class BaseRPC(object):
    """
    A Mixin class for the RPC classes. This class contains methods used by two
    or more RPC/REST classes.
    """
    def getSubAPIs(self):
        """
        Introspect ithe passed API and discover its attributes.
        """
        rpcClass = self.__class__
        for name, apiObj in inspect.getmembers(self.api):
            isAPIInstance = isinstance(apiObj, BaseAPI)
            isProxyInstance = isinstance(apiObj, security.Proxy)
            isPublic = not name.startswith('_')
            if (isAPIInstance or isProxyInstance) and isPublic:
                yield (name, apiObj, rpcClass)

    def setSubHandlers(self):
        """
        This is the magic that:
            1) allows for hierarchical object notation (e.g.,
               parent.child.somemethod), and
            2) adds the data API (and children) to the RPC subhandler data,
               structure, thus fooling the RPC resrouces into thinging that the
               data API methods are their own.
        """
        for name, apiObj, rpcClass in self.getSubAPIs():
            # add a subhandler for every class attribute that subclasses
            # BaseAPI; if the condition is true, then the obj is an API
            # instance (one of api.data.*.*API) and klass is an RPC instance
            # that's going o wrap it so that the sub-API's can get proper rpc
            # subhandling done on them
            self.putSubHandler(name, rpcClass(apiObj, skipHandlers=True))

    def _listFunctions(self):
        """
        Return a list of the names of all the methods that can be used by RPC
        resources.
        """
        names = []
        for name, obj in inspect.getmembers(self):
            if 'rpc_' in name:
                names.append(name)
        for name, obj in inspect.getmembers(self.api):
            typeName = type(obj).__name__
            if not name.startswith('_') and typeName == 'instancemethod':
                names.append(name)
        return names

    def _getFunction(self, functionPath):
        """

        """
        if functionPath.find(self.separator) != -1:
            prefix, functionPath = functionPath.split(self.separator, 1)
            handler = self.getSubHandler(prefix)
            if handler is None:
                raise xmlrpc.NoSuchFunction(self.NOT_FOUND,
                    "no such subHandler %s" % prefix)
            return handler._getFunction(functionPath)
        f = getattr(self.api, functionPath, None)
        if not f:
            raise xmlrpc.NoSuchFunction(self.NOT_FOUND,
                "function %s not found" % functionPath)
        elif not callable(f):
            raise xmlrpc.NoSuchFunction(self.NOT_FOUND,
                "function %s not callable" % functionPath)
        return f

    def setAPI(self, newAPI=None, skipHandlers=False):
        """

        """
        self.api = newAPI
        if not skipHandlers:
            self.setSubHandlers()


class XMLRPCAPI(BaseRPC, xmlrpc.XMLRPC):
    """

    """
    def __init__(self, api=None, skipHandlers=False, *args, **kwds):
        # need to get both api and apiKey here...
        xmlrpc.XMLRPC.__init__(self, *args, **kwds)
        self.setAPI(api)
        self.NoSuchFunction = xmlrpc.NoSuchFunction

    def _cbRender(self, result, request):
        """
        Add to this for custom serializations.
        """
        xmlrpc.XMLRPC._cbRender(self, result, request)


class JSONRPCAPI(BaseRPC, jsonrpc.JSONRPC):
    """

    """
    def __init__(self, api=None, skipHandlers=False, *args, **kwds):
        # need to get both api and apiKey here...
        jsonrpc.JSONRPC.__init__(self, *args, **kwds)
        self.setAPI(api)
        self.NoSuchFunction = jsonrpc.NoSuchFunction


class RESTAPI(ProtecteddRPC, rest.REST):
    """

    """
    def __init__(self, api=None, skipHandlers=False, prefix='REST', *args, **kwds):
        # need to get both api and apiKey here...
        resource.Resource.__init__(self, *args, **kwds)
        self.setAPI(api)
        self.prefix = prefix

    def _parseURI(self, request):
        return request.uri.lstrip('%s/' % self.prefix).split('?')

    def _getFunction(self, functionPath):
        if not functionPath:
            return
        if functionPath.find(self.separator) != -1:
            prefix, functionPath = functionPath.split(self.separator, 1)
            handler = self.children[prefix]
            return handler._getFunction(functionPath)
        return getattr(self.api, functionPath, None)


def rpcAPIFactory(type=''):
    api = data.dataAPIFactory()
    if type == 'XMLRPC':
        rpcAPI = XMLRPCAPI(api)
    elif type == 'JSONRPC':
        rpcAPI = JSONRPCAPI(api)
    elif type == 'REST':
        rpcAPI = RESTAPI(api)
    return rpcAPI


