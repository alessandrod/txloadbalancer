
import hotshot.stats

print "loading stats..."
stats =hotshot.stats.load("pydir.prof")
print "...done"

stats.strip_dirs()
stats.sort_stats('time')

import sys

stdout = sys.stdout
sys.stdout = open("profile.dump", "w")

stats.print_stats()

stats.print_callers()

sys.stdout = stdout
