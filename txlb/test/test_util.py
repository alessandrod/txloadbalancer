from twisted.trial import unittest

from txlb import util


class UtilityTests(unittest.TestCase):
    """
    Test the various utility functions.
    """


    def test_boolify(self):
        """
        Make sure that we get the truth values we expect.
        """
        trues = ['yes', '1', 'on', 'enable', 'true', u'yes', u'1', u'on',
                 u'enable', u'true', 'YES', 'ON', 1, True]
        falses = ['no', '0', 'off', 'disable', 'false', u'no', u'0', u'off',
                 u'disable', u'false', 'NO', 'OFF', 0, False, 'monkeyface']
        for true in trues:
            self.assertEqual(util.boolify(true), True)
        for false in falses:
            self.assertEqual(util.boolify(false), False)


    def test_splitHostPart(self):
        """
        Make sure host strings get split appropriately.
        """
        hosts = ['localhost:8080', '127.0.0.1', '*:80', ':53']
        answers = [
            ('localhost', 8080),
            ('127.0.0.1', 0),
            ('', 80),
            ('', 53)]
        for host, expected in zip(hosts, answers):
            self.assertEquals(util.splitHostPort(host), expected)


    def test_crypting(self):
        """
        Make sure that the password checker is using crypt properly.
        """
        passwd = 's3cr3t5'
        crypted = '..1kBafUApE8U'
        self.assertEquals(util.generateCryptedPass(passwd), crypted)
        self.assertEquals(util.checkCryptPassword(passwd, crypted), True)
