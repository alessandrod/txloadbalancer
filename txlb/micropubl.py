from inspect import getargspec

# a.k.a babybobo. A very small and limited object publisher.
# where possible, it's not tied to any particular mechanism
# (e.g. web)

def patchArgs(argdict):
    " fairly simple hack. all args are lower cased "
    n = {}
    for k,v in argdict.items():
        n[k.lower()] = v
    return n

class uPublisherError(Exception):
    pass

class NotFoundError(uPublisherError):
    pass

class MissingArgumentError(uPublisherError):
    pass

class UnhandledArgumentError(uPublisherError):
    pass

class AccessDenied(uPublisherError):
    pass

class MicroPublisher(object):
    """ a small object publisher """
    published_prefix = "publ_"

    def publish(self, method, args, user):
        args = patchArgs(args)
        if not hasattr(self, '%s%s'%(self.published_prefix, method)):
            raise NotFoundError, "method %s not found"%method
        fnarg = getattr(self, '%s%s'%(self.published_prefix, method))
        self.checkArgs(fnarg, args)
        # check that the user has correct privs
        if not user.checkAccess(fnarg, args):
            raise AccessDenied, "userobject denied access"
        # finally, call the method
        fnarg(**args)


    def checkArgs(self, fn, args):
        arglist, vaarg, kwarg, defargs = getargspec(fn.im_func)
        if arglist[0] == "self":
            arglist = arglist[1:]
        arglist.reverse()
        if defargs:
            argsneeded = arglist[len(defargs):]
        else:
            argsneeded = arglist[:]
        #print arglist, argsneeded, defargs
        # first, check for missing required args
        missing = []
        for a in argsneeded:
            if not args.has_key(a):
                missing.append(a)
        if missing:
            raise MissingArgumentError, \
                "missing argument(s): %s"%(', '.join(missing))
        # now, check if it can handle unknown args (if any provided)
        if 0: #not kwarg:
            provided = args.keys()
            for a in arglist:
                provided.remove(a)
            if provided:
                raise UnhandledArgumentError, \
                    "Additional unhandled argument(s) %s"%(', '.join(provided))
        # all ok to continue. additional checks here
        self.checkPublisherAccess(fn, args)
        return

    def checkPublisherAccess(self, fn, args):
        " override in subclass if desired "
        return
