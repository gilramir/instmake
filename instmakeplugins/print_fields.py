# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Default Print plugin.
"""
from instmakelib import instmake_log as LOG
import sys

description = "Print all fields in a simple multi-line format"

def Print(self, fh=sys.stdout, indent=0, vspace=1):
    print >> fh, "PID\t%s" % (self.pid,)
    print >> fh, "PPID\t%s" % (self.ppid,)
    print >> fh, "CWD\t%s" % (self.cwd,)
    print >> fh, "RETVAL\t%s" % (self.retval,)
    if self.tool:
        print >> fh, "TOOL\t%s" % (self.tool,)

    print >> fh, "DURATION/real\t%s" % (LOG.hms(self.diff_times[self.REAL_TIME]),)
    print >> fh, "DURATION/user\t%s" % (LOG.hms(self.diff_times[self.USER_TIME]),)
    print >> fh, "DURATION/sys\t%s" % (LOG.hms(self.diff_times[self.SYS_TIME]),)
    print >> fh, "DURATION/cpu\t%s" % (LOG.hms(self.diff_times[self.CPU_TIME]),)
    print >> fh, "REAL/start\t%s" % (self.times_start[self.REAL_TIME],)
    print >> fh, "REAL/end\t%s" % (self.times_end[self.REAL_TIME],)

    if self.make_target:
        print >> fh, "TARGET\t%s" % (self.make_target,)

    if self.makefile_filename:
        print >> fh, "MAKEFILE FILE\t%s" % (self.makefile_filename,)

    if self.makefile_lineno:
        print >> fh, "MAKEFILE LINE\t%s" % (self.makefile_lineno,)

    if self.audit_ok != None:
        print >> fh, "AUDIT OK\t%s" % (self.audit_ok,)

    if self.input_files != None:
        for ifile in self.input_files:
            print >> fh, "INPUT FILE\t%s" % (ifile,)

    if self.output_files != None:
        for ofile in self.output_files:
            print >> fh, "OUTPUT FILE\t%s" % (ofile,)

    if self.output_files != None:
        for xfile in self.execed_files:
            print >> fh, "EXECED FILE\t%s" % (xfile,)

    # Environment variables
    if self.env_vars:
        env_var_names = self.env_vars.keys()
        env_var_names.sort()

        for env_var_name in env_var_names:
            print >> fh, "ENV VAR\t%s\t%s" % (env_var_name,
                self.env_vars[env_var_name])


    # Open file descriptors
    if self.open_fds != None:
        print >> fh, "NUM OPEN FDs\t%s" % (len(self.open_fds),)
        print >> fh, "OPEN FDs\t%s" % (", ".join(map(str, self.open_fds)),)

    # Make variables
    if self.make_vars:
        make_var_names = self.make_vars.keys()
        make_var_names.sort()

        for make_var_name in make_var_names:
            # Values
            print >> fh, "MAKE VAR\t%s\t%s" % (make_var_name,
                    self.make_vars[make_var_name])

            # Origins
            print >> fh, "MAKE VAR ORIGIN\t%s\t%s" % (make_var_name,
                    self.make_var_origins[make_var_name])

    print >> fh, "CMDLINE\t%s" % (self.cmdline,)


    if vspace:
        print >> fh
