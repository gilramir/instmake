# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Printer for --csv mode.
"""
import sys

description = "Print selected fields as comma-separated values."

def Print(self, fh=sys.stdout, indent=0, vspace=0):

    if self.make_target == None:
        self.make_target = ""

    if self.makefile_filename == None:
        self.makefile_filename = ""

    if self.makefile_lineno == None:
        self.makefile_lineno = ""

    # Sigh; start with 'P' to keep the spreadsheet from
    # chopping trailing 0's after the decimal point.
    print >> fh, 'P%s,' % (self.pid,),

    if self.tool.find(",") > -1:
        print >> fh, '"%s",' % (self.tool,),
    else:
        print >> fh, '%s,' % (self.tool,),

    if self.tool.find(",") > -1:
        print >> fh, '"%s",' % (self.cwd,),
    else:
        print >> fh, '%s,' % (self.cwd,),
    print >> fh, '%s,' % (self.retval,),

    print >> fh, "%s," % (self.diff_times[self.USER_TIME],),
    print >> fh, "%s," % (self.diff_times[self.SYS_TIME],),
    print >> fh, "%s," % (self.diff_times[self.REAL_TIME],),

    print >> fh, '%s,' % (self.make_target,),
    print >> fh, '%s,' % (self.makefile_filename,),
    print >> fh, '%s,' % (self.makefile_lineno,),

    print >> fh, "%s," % (self.times_start[self.REAL_TIME],),
    print >> fh, "%s" % (self.times_end[self.REAL_TIME],)

    if vspace:
        print >> fh
