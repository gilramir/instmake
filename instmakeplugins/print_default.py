# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Default Print plugin.
"""
from instmakelib import instmake_log as LOG
import sys
import time

description = "Print all fields in multi-line format."

def PrintHeader():
    pass

def PrintFooter():
    pass

def Print(self, fh=sys.stdout, indent=0, vspace=1):
    spaces = "  " * indent
    print >> fh, "%sPID:           " % (spaces,), self.pid
    print >> fh, "%sPPID:          " % (spaces,), self.ppid
    print >> fh, "%sCWD:           " % (spaces,), self.cwd
    print >> fh, "%sRETVAL:        " % (spaces,), self.retval
    if self.tool:
        print >> fh, "%sTOOL:          " % (spaces,), self.tool
    print >> fh, "%sDURATION/real: " % (spaces,), LOG.hms(self.diff_times[self.REAL_TIME])
    print >> fh, "%sDURATION/user: " % (spaces,), LOG.hms(self.diff_times[self.USER_TIME])
    print >> fh, "%sDURATION/sys:  " % (spaces,), LOG.hms(self.diff_times[self.SYS_TIME])
    print >> fh, "%sDURATION/cpu:  " % (spaces,), LOG.hms(self.diff_times[self.CPU_TIME])

    if self.REAL_TIME_IS_CLOCK_TIME:
        print >> fh, "%sREAL/start:    " % (spaces,), self.times_start[self.REAL_TIME], "(", time.ctime(self.times_start[self.REAL_TIME]), ")"
        print >> fh, "%sREAL/end:      " % (spaces,), self.times_end[self.REAL_TIME], "(", time.ctime(self.times_end[self.REAL_TIME]), ")"
    else:
        print >> fh, "%sREAL/start:    " % (spaces,), self.times_start[self.REAL_TIME]
        print >> fh, "%sREAL/end:      " % (spaces,), self.times_end[self.REAL_TIME]

    if self.make_target:
        print >> fh, "%sTARGET:        " % (spaces,), self.make_target

    if self.makefile_filename:
        print >> fh, "%sMAKEFILE FILE: " % (spaces,), self.makefile_filename

    if self.makefile_lineno:
        print >> fh, "%sMAKEFILE LINE: " % (spaces,), self.makefile_lineno

    if self.audit_ok != None:
        print >> fh, "%sAUDIT OK:      " % (spaces,), self.audit_ok

    if self.input_files != None:
        label =      "%sINPUT FILES:   " % (spaces,)
        LOG.print_indented_list(fh, [label], self.input_files)

    if self.output_files != None:
        label =      "%sOUTPUT FILES:  " % (spaces,)
        LOG.print_indented_list(fh, [label], self.output_files)

    if self.execed_files != None:
        label =      "%sEXECED FILES:  " % (spaces,)
        LOG.print_indented_list(fh, [label], self.execed_files)

    # Environment variables
    if self.env_vars:
        labels = []
        values = []
        env_var_names = self.env_vars.keys()
        env_var_names.sort()

        for env_var_name in env_var_names:
            label = "%s${%s}: " % (spaces, env_var_name)
            labels.append(label)
            values.append(self.env_vars[env_var_name])

        LOG.print_indented_list(fh, labels, values)

    # Open file descriptors
    if self.open_fds != None:
        print >> fh, "%sNUM OPEN FDs:  " % (spaces,), len(self.open_fds)
        print >> fh, "%sOPEN FDs:      " % (spaces,), ", ".join(map(str, self.open_fds))

    # Make variables
    if self.make_vars:
        labels = []
        values = []
        make_var_names = self.make_vars.keys()
        make_var_names.sort()

        for make_var_name in make_var_names:
            # Values
            if len(make_var_name) == 1:
                label = "%s$%s: " % (spaces, make_var_name)
            else:
                label = "%s$(%s): " % (spaces, make_var_name)

            labels.append(label)
            values.append(self.make_vars[make_var_name])

            # Origins
            if len(make_var_name) == 1:
                label = "%sorigin $%s: " % (spaces, make_var_name)
            else:
                label = "%sorigin $(%s): " % (spaces, make_var_name)

            labels.append(label)
            values.append(self.make_var_origins[make_var_name])

        LOG.print_indented_list(fh, labels, values)

    # App-inst fields
    if self.app_inst != None:
        labels = []
        values = []
        var_names = self.app_inst.keys()
        var_names.sort()

        for var_name in var_names:
            label = "%s'%s': " % (spaces, var_name)
            labels.append(label)
            values.append(self.app_inst[var_name])

        LOG.print_indented_list(fh, labels, values)

    print >> fh, "%sCMDLINE:       " % (spaces,), self.cmdline


    if vspace:
        print >> fh
