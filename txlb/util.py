import os

from twisted.internet import ssl


privKeyFile = 'etc/server.pem'
certFile = 'etc/server.pem'


def splitHostPort(s):
    """

    """
    h,p = s.split(':')
    p = int(p)
    if h == '*':
        h = ''
    return h,p


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
