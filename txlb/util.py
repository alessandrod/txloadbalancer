import os
import crypt

from twisted.internet import ssl


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


def generateCryptedPass(clearText, seed=''):
    """
    This is a utilty so that there's a single place to go in the code to change
    the password crypt checking, when we need to do that.
    """
    return crypt.crypt(clearText, seed)


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
