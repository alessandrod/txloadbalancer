import os
from setuptools import setup
from setuptools import find_packages

import  txlb

# generic helpers primarily for the long_description; copied from zc.twist
# setup.py
try:
    import docutils
except ImportError:
    def validateReST(text):
        return ''
else:
    import docutils.utils
    import docutils.parsers.rst
    import StringIO
    def validateReST(text):
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

def text(*args, **kwargs):
    # note: distutils explicitly disallows unicode for setup values :-/
    # http://docs.python.org/dist/meta-data.html
    tmp = []
    for a in args:
        if a in ['README'] or a.endswith('.txt'):
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
    out = kwargs.get('out')
    if out is True:
        out = 'TEST_THIS_REST_BEFORE_REGISTERING.txt'
    if out:
        f = open(out, 'w')
        f.write(res)
        f.close()
        report = validateReST(res)
        if report:
            print report
            raise ValueError('ReST validation error')
    return res
# end helpers; below this line should be code custom to this package
setup(
    name=txlb.name,
    version=txlb.version,
    description=txlb.description,
    author="Duncan McGreggor, Anthony Baxter",
    author_email="oubiwann@divmod.com",
    url=txlb.projectURL,
    packages=find_packages(),
    scripts=['bin/txlb.tac'],
    long_description=text('README', out=False),
    zip_safe=False,
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
