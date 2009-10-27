from txlb import meta
from txlb.util import dist


dist.setup(
    name=meta.display_name,
    version=meta.version,
    description=meta.description,
    author=meta.author,
    author_email=meta.author_email,
    url=meta.url,
    packages=dist.findPackages(meta.library_name),
    scripts=["bin/txlb.tac"],
    long_description=dist.catReST(
        "docs/PRELUDE.txt",
        "README",
        "docs/DEPENDENCIES.txt",
        "docs/INSTALL.txt",
        "docs/USAGE.txt",
        "docs/PERFORMANCE.txt",
        "docs/HISTORY.txt",
         out=True),
    license=meta.license,
    classifiers=[
       "Development Status :: 5 - Production/Stable",
       "Environment :: Web Environment",
       "Environment :: No Input/Output (Daemon)",
       "License :: OSI Approved :: Python Software Foundation License",
       "Operating System :: POSIX",
       "Operating System :: MacOS :: MacOS X",
       "Operating System :: Microsoft",
       "Programming Language :: Python",
       "Intended Audience :: System Administrators",
       "Intended Audience :: Developers",
       "Topic :: Internet",
       "Topic :: System :: Networking",
    ]

)
