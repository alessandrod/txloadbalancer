import txlb
from txlb import util


util.setup(
    name=txlb.name,
    version=txlb.version,
    description=txlb.description,
    author="Duncan McGreggor, Anthony Baxter",
    author_email="oubiwann@divmod.com",
    url=txlb.projectURL,
    packages=util.find_packages(),
    scripts=['bin/txlb.tac'],
    long_description=util.catReST(
        'README',
        'DEPENDENCIES',
         out=False),
    license='MIT',
    classifiers=[
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
