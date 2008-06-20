import pdlogging
try:
    import twisted
    from pdnetworktwisted import *
except ImportError:
    pdlogging.log("no twisted available - falling back to asyncore")
    from pdnetworkasyncore import *
