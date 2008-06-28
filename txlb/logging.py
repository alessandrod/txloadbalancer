Logger=None

import sys, time


# XXX
# look at replacing this later; can probably just use twisted's logging
class _LoggerClass:
    def __init__(self, logfile=None):
        self.logfile = logfile
        self.fp = None
        self.reopen()

    def reopen(self):
        if self.logfile is not None and self.fp is not None:
            del self.fp
        if self.logfile is None:
            self.fp = sys.stderr
        else:
            self.fp = open(self.logfile, 'a')

    def log(self, message, datestamp=0):
        if datestamp:
            self.fp.write("%s %s"%(self.log_date_time_string(),message))
        else:
            self.fp.write(message)
        self.fp.flush()

    def log_date_time_string(self):
        """Return the current time formatted for logging."""
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        s = "%02d/%02d/%04d %02d:%02d:%02d" % (
                day, month, year, hh, mm, ss)
        return s


def initlog(filename):
    global Logger
    Logger = _LoggerClass(filename)


def log(message, datestamp=0):
    global Logger
    if Logger is None: Logger = _LoggerClass()
    Logger.log(message, datestamp)


def reload():
    global Logger
    if Logger is None: Logger = _LoggerClass()
    Logger.reload()
