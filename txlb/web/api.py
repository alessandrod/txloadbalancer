"""
Important notes:
 * The classes in this package are used to dynamically generate three separate
   RPC APIs. As such, there are not 4 APIs to maintain, just this one. However,
   this may make the RPC code look like black magic -- but everything's cool;
   no chickens were sacrificed making this work.

 * All methods of classes in this module need to return results that are
   serializable over XML-RPC, JSON-RPC, and REST.

 * The code that does the magic of turning regular data API methods into RPC
   methods with serializable output is in rpc.BaseRPC, and is
   Twisted-specific.
"""
class BaseAPI(object):
    """

    """

class ConfigAPI(BaseAPI):
    """

    """
    def getXML(self):
        pass

    def getJSON(self):
        pass

    def getRepr(self):
        pass

class ManagerAPI(BaseAPI):
    """

    """

class TestAPI(BaseAPI):
    """
    For testing purposes only; makes no database queries nor any object state
    changes. Safe for testing usage, even on prodcution machines.
    """
    def echo(self, text):
        return text

    def add(self, a, b):
        return a + b


class DataAPI(object):
    """
    The top-level hierarchy for the API subhandlers.

    Note that the primary API instances are set by the dataAPIFactory factory.
    As such, this API is not usable via direct instantiation; the factory has
    to be used.
    """
    pass

def getAttrAPIMap():
    """
    Return a dictionary whose keys are the desired API attributes for the
    subhandlers and whose values are the classes that will eventually be
    instantiated and assigned to the corresponding attribute.
    """
    return {
        'test': TestAPI,
        'config': ConfigAPI,
        'manager': ManagerAPI,
        }

def apiFactory(apiArgs=[], apiKwds={}, api=None, makeInstances=False,
               instanceArgs=[], instanceKwds={}):
    """
    This is an API factory that is capable of building either the standard
    DataAPI (with various options) or the AnonymousAPI.

    This factory was created because under certain circumstances, one does not
    want API sub-APIs created as instances, but rather as classes that can be
    instantiated (or replaced) later. At the same time, one doesn't want to
    have to maintain two class instances that are essentially identical, except
    for when they do the instantiation of their sub-APIs. The factory lets us
    accomplish alll of these things.
    """
    apiInstance = api(*apiArgs, **apiKwds)
    for attr, klass in getAttrAPIMap().items():
        if makeInstances:
            instance = klass(*instanceArgs, **instanceKwds)
            setattr(apiInstance, attr, instance)
        else:
            setattr(api, attr, klass)
            apiInstance.methodParams = instanceKwds
    return apiInstance


def dataAPIFactory(makeInstances=True):
    """
    This is a convenience factory for creating a DataAPI instance.
    """
    kwds = {}
    api = DataAPI
    apiArgs = []
    return apiFactory(instanceKwds=kwds, makeInstances=makeInstances,
                      api=api, apiArgs=apiArgs)


dataAPI = dataAPIFactory()


