import os
import re
import crypt

from twisted.internet import ssl

import txlb

privKeyFile = 'etc/server.pem'
certFile = 'etc/server.pem'



def boolify(data):
    """
    First, see if the data adheres to common string patterns for a boolean.
    Failing that, treat it like a reglar python object that needs to be checked
    for a truth value.
    """
    trues = ['yes', '1', 'on', 'enable', 'true']
    if isinstance(data, str) or isinstance(data, unicode):
        data = str(data)
        if data.lower() in trues:
            return True
        return False
    return bool(data)



def splitHostPort(hostPortString):
    """
    A utility needed for converting host:port string values in configuration
    files to a form that is actually useful.
    """
    hostPort = hostPortString.split(':')
    if len(hostPort) == 1:
        # this means no port was passed
        host = hostPort[0]
        port = 0
    else:
        host, port = hostPort
    port = int(port)
    if host == '*':
        host = ''
    return (host, port)



def createCertificate():
    """

    """
    # this is copied from test_sslverify.py
    dn = ssl.DistinguishedName(commonName="PyDirector HTTPS")
    keypair = ssl.KeyPair.generate()
    req = keypair.certificateRequest(dn)
    certData = keypair.signCertificateRequest(
        dn, req, lambda dn: True, 132)
    return keypair.newCertificate(certData)



def createSSLFile():
    """

    """
    kp = createCertificate()
    fh = open(certFile, 'w+')
    fh.write(kp.dumpPEM())
    fh.close()
    print "Generated key/cert file '%s'." % certFile



def setupServerCert():
    """

    """
    if not os.path.exists(certFile):
        createSSLFile()
    else:
        print "Cert file '%s' exists; not creating." % certFile



def generateCryptedPass(clearText, seed='..'):
    """
    This is a utilty so that there's a single place to go in the code to change
    the password crypt checking, when we need to do that.
    """
    return crypt.crypt(clearText, seed)


def checkCryptPassword(clearText, check):
    """
    A utility function for checking the authenticity of a password.
    """
    seed = check[:2]
    crypted = generateCryptedPass(clearText, seed)
    if crypted == check:
        return True
    return False


def getNamespace(namespace):
    """
    This was originally intended to be used by the setup function for the admin
    SSH server, but there's no reason it can't be used elsewhere.
    """
    import txlb
    limitedNamespace = namespace
    thisNamespace = globals()
    thisNamespace.update(locals())
    for key in ('__builtins__', '__doc__', 'help', 'txlb'):
        if key in thisNamespace:
            limitedNamespace[key] = thisNamespace[key]
    return limitedNamespace


def reprNestedObjects(obj, padding=u'', skip=[]):
    """
    A utility function for iterating an object's attributes and providing a
    unicode representation of that object and it's "contents."
    """
    nl = u'\n'
    output = ''
    if obj == None:
       output += repr(obj)
    elif True in [isinstance(obj, x) for x in [str, int, float]]:
        output += unicode(obj)
    elif isinstance(obj, unicode):
        output += obj
    elif isinstance(obj, list) or isinstance(obj, tuple):
        output += repr(obj)
    elif isinstance(obj, dict):
        output += nl
        padding += u'  '
        for key, val in obj.items():
            output += padding + unicode(key) + ':'
            output += reprNestedObjects(val, padding)
        output += nl
    elif hasattr(obj, '__dict__'):
        #output += nl
        output += reprNestedObjects(obj.__dict__, padding)
    else:
        output += nl
        output += repr(obj)
    return re.sub('\n\n', '\n', output)



def setup(*args, **kwds):
    """
    Compatibility wrapper.
    """
    try:
        from setuptools import setup
    except ImportError:
        from distutils.core import setup
    return setup(*args, **kwds)



def find_packages():
    """
    Compatibility wrapper.

    Taken from storm setup.py.
    """
    try:
        from setuptools import find_packages
        return find_packages()
    except ImportError:
        pass
    packages = []
    for directory, subdirectories, files in os.walk("txlb"):
        if '__init__.py' in files:
            packages.append(directory.replace(os.sep, '.'))
    return packages


def hasDocutils():
    """
    Check to see if docutils is installed.
    """
    try:
        import docutils
        return True
    except ImportError:
        return False



def _validateReST(text):
    """
    Make sure that the given ReST text is valid.

    Taken from Zope Corp's zc.twist setup.py.
    """
    import docutils.utils
    import docutils.parsers.rst
    import StringIO

    doc = docutils.utils.new_document('validator')
    # our desired settings
    doc.reporter.halt_level = 5
    doc.reporter.report_level = 1
    stream = doc.reporter.stream = StringIO.StringIO()
    # docutils buglets (?)
    doc.settings.tab_width = 2
    doc.settings.pep_references = doc.settings.rfc_references = False
    doc.settings.trim_footnote_reference_space = None
    # and we're off...
    parser = docutils.parsers.rst.Parser()
    parser.parse(text, doc)
    return stream.getvalue()



def validateReST(text):
    """
    A wrapper that ensafens the validation for pythons that are not embiggened
    with docutils.
    """
    if hasDocutils():
        return _validateReST(text)
    print " *** No docutils; can't validate ReST."
    return ''



def catReST(*args, **kwds):
    """
    Concatenate the contents of one or more ReST files.

    Taken from Zope Corp's zc.twist setup.py.
    """
    # note: distutils explicitly disallows unicode for setup values :-/
    # http://docs.python.org/dist/meta-data.html
    tmp = []
    for a in args:
        if a in ['README', 'DEPENDENCIES'] or a.endswith('.txt'):
            f = open(os.path.join(*a.split('/')))
            tmp.append(f.read())
            f.close()
            tmp.append('\n\n')
        else:
            tmp.append(a)
    if len(tmp) == 1:
        res = tmp[0]
    else:
        res = ''.join(tmp)
    out = kwds.get('out')
    if out is True:
        out = 'CHECK_THIS_BEFORE_UPLOAD.txt'
    if out:
        f = open(out, 'w')
        f.write(res)
        f.close()
        report = validateReST(res)
        if report:
            print report
            raise ValueError('ReST validation error')
    return res
