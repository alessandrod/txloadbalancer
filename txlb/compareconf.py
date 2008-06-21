class DiffError(Exception): pass

def diffXML(oldxml, newxml):
    from pydirector.pdconf import PDConfig
    ret = []
    oldconf = PDConfig(xml=oldxml)
    newconf = PDConfig(xml=newxml)
    ret.extend( compareServices(oldconf, newconf) )
    ret.extend( compareAdmin(oldconf, newconf) )
    ret.extend( compareLogging(oldconf, newconf) )
    return ret

def compareServices(oldconf, newconf):
    ret = []
    oldservices = oldconf.services.keys()
    oldservices.sort()
    newservices = newconf.services.keys()
    newservices.sort()
    if oldservices != newservices:
        # would we want to enable new services this way?
        raise DiffError, "can't handle different services list"
    for serviceName in oldservices:
        os = oldconf.services[serviceName]
        ns = newconf.services[serviceName]
        ret.extend(compareListeners(serviceName, os, ns))
        ret.extend(compareGroups(serviceName, os, ns))
        ret.extend(compareEnable(serviceName, os, ns))
    return ret


def compareGroups(serviceName, oldservice, newservice):
    ret = []
    oldgroups = oldservice.groups.keys()
    oldgroups.sort()
    newgroups = newservice.groups.keys()
    newgroups.sort()
    if oldgroups != newgroups:
        # maybe change this after adding 'newGroup' to the api
        raise DiffError, \
            "can't handle different groups list for %s"%serviceName
    for groupName in oldgroups:
        og = oldservice.groups[groupName]
        ng = newservice.groups[groupName]
        ret.extend(compareHosts(serviceName, groupName, og, ng))
        if og.scheduler != ng.scheduler:
            ret.append(("changeScheduler",
                {'service'  : serviceName,
                 'group'    : groupName,
                 'scheduler': ng.scheduler}))
    return ret

def compareHosts(serviceName, groupName, oldgroup, newgroup):
    ret = []
    oldhosts = oldgroup.hosts.keys()
    oldhosts.sort()
    newhosts = newgroup.hosts.keys()
    newhosts.sort()
    allhosts = mergelists(oldhosts,newhosts)
    for host in allhosts:
        if host in oldhosts and host in newhosts:
            continue
        elif host in newhosts:
            newhost = newgroup.getHost(host)
            ret.append(("addHost",
                {'service' : serviceName,
                 'group'   : groupName,
                 'ip'      : newhost.ip,
                 'name'    : newhost.name }))
        elif host in oldhosts:
            oldhost = oldgroup.getHost(host)
            ret.append(("delHost",
                {'service' : serviceName,
                 'group'   : groupName,
                 'ip'      : oldhost.ip }))
        else:
            raise DiffError, "what the hey?"
    return ret

def mergelists(l1, l2):
    d = {}
    for i in l1+l2:
        d[i] = 1
    l = d.keys()
    l.sort()
    return l

def compareEnable(serviceName, oldservice, newservice):
    ret = []
    # to do. or not? do we care?
    return ret

def compareListeners(serviceName, oldservice, newservice):
    ret = []
    # how do we handle this? no API for listener changes
    return ret

def compareAdmin(oldconf, newconf):
    ret = []
    if oldconf.admin is None and newconf.admin is None:
        # both empty
        return ret
    if oldconf.admin is None or newconf.admin is None:
        raise DiffError, "can't handle enabling/disabling admin"
    else:
        # we should also handle looking at the listen (and secure,
        # when added). needs web api commands.
        compareUsers(oldconf.admin.userdb, newconf.admin.userdb)
    return ret

def compareUsers(olduserdb, newuserdb):
    ret = []
    oldusers = olduserdb.keys()
    oldusers.sort()
    newusers = newuserdb.keys()
    newusers.sort()
    allusers = mergelists(oldusers,newusers)
    for user in allusers:
        if user in oldusers and user in newusers:
            ou = olduserdb.get(user)
            nu = newuserdb.get(user)
            if ou.password != nu.password or ou.access != nu.access:
                # user has changed!
                ret.append(("delUser",
                    {'name'     : user }))
                ret.append(("addUser",
                    {'name'     : user,
                     'password' : nu.password,
                     'access'   : nu.access }))
        elif user in newusers:
            nu = newuserdb.get(user)
            ret.append(("addUser",
                {'name'     : user,
                 'password' : nu.password,
                 'access'   : nu.access }))
        elif user in oldusers:
            ret.append(("delUser",
                {'name'     : user }))
        else:
            raise DiffError, "what the hey - user %s?"%user
    return ret


def compareLogging(oldconf, newconf):
    ret = []
    # should handle this - changing logfile location?
    return ret

if __name__ == "__main__":
    import sys
    ret = diffXML(open(sys.argv[1]).read(),
                  open(sys.argv[2]).read())
    ret.sort()
    for r in ret: print r
