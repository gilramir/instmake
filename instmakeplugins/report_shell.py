# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Show records that GNU make would have used the shell to run
instead of using fork/exec.
"""
from instmakelib import instmake_log as LOG
import getopt
import sys
import os

description = "Show records that GNU make would have used system() to build"

def usage():
    print description
    print "usage:"
    print "\tshell [OPTIONS]"
    print "\t\t-v  Reverse -- show non-system() jobs."
    print "\t\t-r  Show rules instead of processes."



# From GNU make 3.79.1, job.c
sh_chars = "#;\"*?[]&|<>(){}$`^"
sh_cmds = [
    "cd", "eval", "exec", "exit", "login",
    "logout", "set", "umask", "wait", "while", "for",
    "case", "if", ":", ".", "break", "continue",
    "export", "read", "readonly", "shift", "times",
    "trap", "switch" ]

def uses_system(rec):
    """Would the command in the record be invoked via system()
    by GNU make? Returns 1 if Yes, 0 if No."""
    # trivial algorithm
    cmd = rec.cmdline
    first_arg = rec.cmdline_args[0]

    # jmake records some actions and labels them as make-internal-function
    # Don't look for special characters in these records.
    if first_arg == "make-internal-function":
        return 0
    else:
        # Check the first argument.
        if first_arg in sh_cmds:
            return 1

    # Check the chars in the command-line for the special chars.
    for c in cmd:
        if c in sh_chars:
            return 1

    return 0

# What to show to the user... procs or rules.
SHOW_PROCS = 0
SHOW_RULES = 1

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'shell' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Defaults
    show_what = SHOW_PROCS 
    opposite = 0

    # Our options
    optstring = "vr"
    longopts = []


    # Process the command-line options.
    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-v":
            opposite = 1
        elif opt == "-r":
            show_what = SHOW_RULES
        else:
            sys.exit("%s option not handled." % (opt,))

    # Open the log file
    log = LOG.LogFile(log_file_name)

    if show_what == SHOW_PROCS:
        report_procs(log, opposite)

    elif show_what == SHOW_RULES:
        report_rules(log, opposite)

    else:
        sys.exit("Unhandled show_what value.")


def report_procs(log, opposite):
    """Read the log file and report the procs to the user."""
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        if opposite:
            if not uses_system(rec):
                rec.Print()
        else:
            if uses_system(rec):
                rec.Print()

def report_rules(log, opposite):
    """Read the log file and report the rules to the user."""
    recs = []

    # We'll read the file and store the interested records
    # to the array.
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        if opposite:
            if not uses_system(rec):
                recs.append(rec)
        else:
            if uses_system(rec):
                recs.append(rec)


    # Now we uniquify the rules mentioend by the recs, and
    # convert makefile filenames to absolute paths based on the
    # rec's CWD if the filename is not already absolute.
    rules = {}
    for rec in recs:
        # No makefile/lineno data? Report that fact tot he suer.
        if not rec.makefile_filename or not rec.makefile_lineno:
            print "No makefile/lineno info for PID %s:" % (rec.pid,)
            print "\t", rec.cmdline
            print
            continue

        # Make sure the makefile name is absolute.
        if not os.path.isabs(rec.makefile_filename):
            makefile = os.path.join(rec.cwd, rec.makefile_filename)
        else:
            makefile = rec.makefile_filename
        makefile = rec.makefile_filename

        # Save the data to the hashes. rules[makefile][lineno] = None
        linenos = rules.setdefault(makefile, {})
        linenos[rec.makefile_lineno] = None

    # Report to the user, sorted by makefile, then line number.
    makefiles = rules.keys()
    makefiles.sort()

    for makefile in makefiles:
        linenos = rules[makefile].keys()
        linenos.sort()

        for lineno in linenos:
            # Print with a + before the line number so that the
            # line can be copied-and-pasted to a vim or emacs command-line
            # to have the editor open the file exactly at that line number.
            print "%s +%s" % (makefile, lineno)



