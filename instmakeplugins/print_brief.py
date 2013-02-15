# Copyright (c) 2010 by Cisco Systems, Inc.
"""
brief summary - PID, duration(real), CWD, part of cmdline
"""
from instmakelib import instmake_log as LOG
import sys

description = "Very brief summary."

def PrintHeader():
    pass

def PrintFooter():
    pass

def Print(self, fh=sys.stdout, indent=0, vspace=0):
    spaces = "  " * indent

    duration = LOG.hms(self.diff_times[self.REAL_TIME])

    if len(self.cmdline) < 50:
        cmdline = self.cmdline
    else:
        cmdline = self.cmdline[:47] + "..."

    print >> fh, "%s%s (%s) %s %s %s" % (spaces, self.pid, self.tool,
            duration, self.cwd, cmdline)

    if vspace:
        print >> fh
