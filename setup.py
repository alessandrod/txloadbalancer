from setuptools import setup
from setuptools import find_package

import  txlb

setup(
    name = txlb.name
    version = txlb.version,
    description = "txLoadBalancer - A Twisted-based TCP load balancer.",
    author = "Duncan McGreggor, Anthony Baxter",
    author_email = "oubiwann@divmod.com, anthony@interlink.com.au",
    url = 'https://launchpad.net/txloadbalancer',
    packages = setuptools.find_packages(),
    scripts = ['bin/txlb.tac'],
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
