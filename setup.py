from setuptools import setup

import  txlb

setup(
    name = txlb.name
    version = txlb.version,
    description = "txLoadBalancer - A Twisted-based TCP load balancer.",
    author = "Anthony Baxter, Duncan McGreggor",
    author_email = "anthony@interlink.com.au, oubiwann@divmod.com",
    url = 'https://launchpad.net/txloadbalancer',
    packages = setuptools.find_packages(txlb.shortName.lower()),
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
