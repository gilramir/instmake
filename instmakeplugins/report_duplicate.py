# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Report duplicate actions: same action in same workding dir.
"""

import getopt
import sys
from instmakelib import instmake_log as LOG

def make_key(dir, cmdline):
    """Make a single string, combining multiple fields."""
    return dir + "|" + cmdline

def report_duplicate(records, same_wd):
    """Report an instance of duplicate actions."""

    # Print info that is the same for all records
    rec0 = records[0]
    if rec0.tool:
        print "Tool:", rec0.tool

    if same_wd:
        print "Working Directory:", rec0.cwd

    print "Command-line:", rec0.cmdline

    i = 1
    for rec in records:
        print "\t%3d. PPID=%s PID=%s" % (i, rec.ppid, rec.pid),

        if not same_wd:
            print "CWD=%s" % (rec.cwd,),

        if rec.make_target:
            print "TARGET=%s" % (rec.make_target,),

        if rec.makefile_filename:
            print "RULE=%s:%s" % (rec.makefile_filename,
                rec.makefile_lineno),
        print
        i += 1
    print

description = "Report duplicate jobs in same working directory."

def usage():
    print "duplicate:", description
    print "\t-a : show duplicate jobs in ANY directory"

def report(log_file_names, args):

    # Get the single log file name
    if len(log_file_names) != 1:
        sys.exit("'duplicate' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = "ca"
    longopts = []

    # We don't have any options
    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    same_wd = 1

    for opt, arg in opts:
        if opt == "-a":
            same_wd = 0
        else:
            assert 0, "%s option not handled." % (opt,)

    # Open the log file
    log = LOG.LogFile(log_file_name)

    # Read the log records
    records = {}
    duplicates = {}
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        # Retrieve the fields we're interested in.
        dir = rec.cwd
        cmdline = rec.cmdline

        # Create the key for the hash. The value is the 'rec'
        if same_wd:
            key = make_key(dir, cmdline)
        else:
            key = make_key("", cmdline)

        # Insert into hash, checking for duplicates.
        # Put duplicates in the duplicate hash. 
        array = records.setdefault(key, [])
        array.append(rec)
        if len(array) > 1:
            duplicates[key] = array

    # Report the duplicates
    for recs in duplicates.values():
        report_duplicate(recs, same_wd)
