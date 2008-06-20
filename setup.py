
from distutils.core import setup

from pydirector import Version

# patch distutils if it can't cope with the "classifiers" keyword.
# this just makes it ignore it.
import sys
if sys.version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None

setup(
    name = "pydirector",
    version = Version,
    description = "Python Director - TCP load balancer.",
    author = "Anthony Baxter",
    author_email = "anthony@interlink.com.au",
    url = 'http://sourceforge.net/projects/pythondirector/',
    packages = ['pydirector'],
    scripts = ['pydir.py'],
    classifiers = [
       'Development Status :: 5 - Production/Stable',
       'Environment :: Web Environment',
       'Environment :: No Input/Output (Daemon)',
       'License :: OSI Approved :: Python Software Foundation License',
       'Operating System :: POSIX',
       'Operating System :: MacOS :: MacOS X',
       'Operating System :: Microsoft',
       'Programming Language :: Python',
       'Intended Audience :: System Administrators',
       'Intended Audience :: Developers',
       'Topic :: Internet',
       'Topic :: System :: Networking',
    ]

)
