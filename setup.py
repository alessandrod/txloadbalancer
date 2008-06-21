from distutils.core import setup

from pydirector import Version

setup(
    name = "pydirector",
    version = Version,
    description = "Python Director - TCP load balancer.",
    author = "Anthony Baxter, Duncan McGreggor",
    author_email = "anthony@interlink.com.au, oubiwann@divmod.com",
    url = 'https://launchpad.net/pydirector',
    packages = ['pydirector'],
    scripts = ['bin/pydir.py', 'bin/pydir++.py', 'bin/pydir.tac'],
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
