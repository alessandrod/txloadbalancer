import re
from urllib import unquote

from twisted.python import log
from twisted.internet import defer
from twisted.web import resource, server

def serialize(item):
    if item.lower() in ['true', 'false']:
        return bool(item)
    if re.match('^[0-9]+$', item):
        return int(item)
    elif re.match('^[0-9.]+$', item):
        return float(item)
    else:
        return unquote(item)

class UriQuery(object):
    '''
    Taken from a recipe by Duncan McGreggor on the ASPN Python Cookbook:
        http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473864

    >>> query = UriQuery('num=100&q=twisted+python&btnG=Search')
    >>> query['q']
    'twisted+python'
    >>> k = query.keys()
    >>> k.sort()
    >>> k
    ['btnG', 'num', 'q']
    >>> v = query.values()
    >>> v.sort()
    >>> v
    [100, 'Search', 'twisted+python']

    # Single arg
    >>> query = UriQuery('apple')
    >>> query.args
    ['apple']

    # Multiple args
    >>> query = UriQuery('apple&banana&cranberry')
    >>> query.args
    ['apple', 'banana', 'cranberry']

    # Mixed args and kwds
    >>> query = UriQuery('apple&banana&limit=20&fraction=0.75')
    >>> query.args
    ['apple', 'banana']
    >>> query.kwds
    {'limit': 20, 'fraction': 0.75}

    # neither
    >>> query = UriQuery('')
    >>> query.args
    []
    >>> query.kwds
    {}
    '''
    illegalVars = ['stringValue', 'args', 'kwds']

    def __init__(self, query):
        self.args = []
        self.kwds = {}
        parts = query.split('&')
        for part in parts:
            if '=' in part:
                key, val = part.split('=')
                self.update(dict(((key, serialize(val)),)))
            elif part:
                self.append(serialize(part))
        for key, val in self.kwds.items():
            if not key in self.illegalVars:
                setattr(self, key, val)

    def __getitem__(self, key):
        if isinstance(key, int):
            try:
                return self.args[key]
            except IndexError:
                pass
        return self.kwds[key]

    def __setitem__(self, key, val):
        self.kwds[key] = val

    def __len__(self):
        return len(self.args) + len(self.kwds.keys())

    def append(self, element):
        self.args.append(element)

    def update(self, *args, **kwds):
        self.kwds.update(*args, **kwds)

    def keys(self):
        return self.kwds.keys()

    def values(self):
        return self.kwds.values()

    def items(self):
        return self.kwds.items()


class REST(resource.Resource):

    addSlash = False
    isLeaf = True
    separator = '/'

    def _getFunction(self, functionPath):
        if not functionPath:
            return
        if functionPath.find(self.separator) != -1:
            prefix, functionPath = functionPath.split(self.separator, 1)
            handler = self.children[prefix]
            return handler._getFunction(functionPath)

        return getattr(self, "rest_%s" % functionPath, None)

    def _parseURI(request):
        """
        >>> class FakeRequest:
        ...   def __init__(self, uri):
        ...     self.uri = uri
        >>> uri = '/path/to/some/resource?and&params&p=I%20want&q=to%20pass'
        >>> request = FakeRequest(uri)
        >>> REST._parseURI(request)
        ['path/to/some/resource', 'and&params&p=I%20want&q=to%20pass']
        """
        return request.uri.lstrip('/').split('?')

    _parseURI = staticmethod(_parseURI)

    def render(self, request):
        request.content.seek(0, 0)
        request.setHeader("content-type", "text/plain")
        uriParts = self._parseURI(request)
        functionPath = uriParts.pop(0)
        if uriParts:
            queryString = uriParts.pop()
        else:
            queryString = ''
        query = UriQuery(queryString)
        function = self._getFunction(functionPath)
        if not function:
            return ''
        if query.args and query.kwds:
            d = defer.maybeDeferred(function, *query.args, **query.kwds)
        elif query.args:
            d = defer.maybeDeferred(function, *query.args)
        elif query.kwds:
            d = defer.maybeDeferred(function, **query.kwds)
        else:
            d = defer.maybeDeferred(function)
        d.addErrback(self._ebNotify, request)
        d.addCallback(self._cbRender, request)
        return server.NOT_DONE_YET

    def _ebNotify(self, failure, request):
        log.err(failure)
        request.write(failure.getErrorMessage())
        request.finish()

    def _cbRender(self, result, request):
        request.write(str(result) or '')
        request.finish()

    def putSubHandler(self, *args, **kwds):
        self.putChild(*args, **kwds)

def _test():
    import doctest
    doctest.testmod()

if __name__ == '__main__':
    _test()
