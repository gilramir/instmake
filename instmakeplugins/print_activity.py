# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Print plugin to show $@ and tool.
"""
import sys

description = "One-line summary showing $@, if available, and TOOL"

def PrintHeader():
    pass

def PrintFooter():
    pass

def Print(self, fh=sys.stdout, indent=0, vspace=0):
    spaces = "  " * indent

    why = self.make_vars.get("@", "")

    if why:
        print >> fh, "%s%s: %s (%s)" % (spaces, self.pid, self.tool, why)
    else:
        print >> fh, "%s%s: %s" % (spaces, self.pid, self.tool)

    if vspace:
        print >> fh
