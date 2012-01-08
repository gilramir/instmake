# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Print plugin to show $@ and tool.
"""
from instmakelib import instmake_log as LOG
import sys
import os

description = "One-line summary showing $@, if available, and TOOL"

def Print(self, fh=sys.stdout, indent=0, vspace=0):
    spaces = "  " * indent

    why = self.make_vars.get("@", "")

    if why:
        print >> fh, "%s%s: %s (%s)" % (spaces, self.pid, self.tool, why)
    else:
        print >> fh, "%s%s: %s" % (spaces, self.pid, self.tool)

    if vspace:
        print >> fh
