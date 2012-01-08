# Copyright (c) 2010 by Cisco Systems, Inc.
"""
'grep'-like Print plugin.
"""
from instmakelib import instmake_log as LOG
import sys
import os

description = "One-line summary in 'grep -n'-like format."

def Print(self, fh=sys.stdout, indent=0, vspace=0):
    spaces = "  " * indent


    if self.makefile_filename:
        makefile = os.path.join(self.cwd, self.makefile_filename)
    else:
        makefile = os.path.join(self.cwd, '???')

    if self.makefile_lineno:
        lineno = self.makefile_lineno
    else:
        lineno = "???"

    print >> fh, "%s%s:%s:%s" % (spaces, makefile, lineno, self.cmdline)

    if vspace:
        print >> fh
