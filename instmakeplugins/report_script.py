# Copyright (c) 2011 by Cisco Systems, Inc.
"""
Produce shell scripts for one ore more commands
"""
import sys
import getopt
from instmakelib import instmake_log as LOG

description = "Create a shell script to run commands"

def usage():
    print "script:", description
    print "   -p PID        Produce a script for this PID (can use multiple)"

def report(log_file_names, args):
    pids = []

    optstring = "p:"

    try:
        opts, args = getopt.getopt(args, optstring)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-p":
            pids.append(arg)
        else:
            sys.exit("Unexpected option: " + opt)

    if args:
        sys.exit("No arguments are accepted.")

    # We only accept one log file
    if len(log_file_names) != 1:
        # XXX - it could support > 1
        sys.exit("'script' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Open the log file
    log = LOG.LogFile(log_file_name)

    # Handle a bunch of possibly-unrelated records
    records = []

    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        # Selecting on PID?
        if pids:
            if rec.pid in pids:
                records.append(rec)
                pids.remove(rec.pid)
                if len(pids) == 0:
                    break

        # Selecting all records?
        else:
            records.append(rec)

    if len(records) == 0:
        sys.exit("No records found.")

    # Sort and report
    records.sort(lambda x,y : cmp(x.RealStartTime(), y.RealStartTime()))

    print "#!/bin/bash"
    print "set -e"
    print "set -x"
    print

    for rec in records:
        print "function %s () {" % (symbol_from_pid(rec.pid),)
        if rec.env_vars:
           env_var_names = rec.env_vars.keys()
           env_var_names.sort()
           for env_var_name in env_var_names:
               print "\texport %s=%s" % (env_var_name,
                       shell_esc(rec.env_vars[env_var_name]))

        print "\tcd %s" % (rec.cwd,)
        print "\t%s" % (rec.cmdline,)
        print "}"
        print

#    print "start_dir=$(pwd)"
    for rec in records:
        print "( %s )" % (symbol_from_pid(rec.pid),)
#    print "cd ${start_dir}"


def symbol_from_pid(pid):
    text = pid.replace(".", "_")
    return "pid_" + text

def shell_esc(txt):
    """Return a double-quoted string, with all special characters
    properly escaped."""
    new = str(txt)

    # Escape dollar signs (variable references)
    new = new.replace("$", "\\$")

    # Escape double quotes.
    new = new.replace('"', '\\"')

    # Escape back-ticks
    new = new.replace('`', '\\`')

    return '"' + new + '"'

