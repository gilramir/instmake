# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Concatenate multiple logs into one new log.
"""
import getopt
import sys
import os
import cPickle as pickle
from instmakelib import instmake_log as LOG
from instmakelib import instmake_build

ASSUME_DEFAULT_LOGFILE = 0

INSTMAKE_VERSION = LOG.INSTMAKE_VERSION_12

class FakeRec:
    ppid = None
    pid = None
    cwd = None
    retval = None
    times_start = None
    times_end = None
    cmdline_args = None
    make_target = None
    makefile_filename = None
    makefile_lineno = None
    env_vars = None
    open_fds = None

def write_rec(rec, fd):
    empty_audit_data = None
    empty_make_vars = {}

    # Version 12 record. We lose the audit info and the make_vars info
    data = (rec.ppid, rec.pid, rec.cwd, rec.retval, rec.times_start,
            rec.times_end, rec.cmdline_args, rec.make_target,
            rec.makefile_filename, rec.makefile_lineno, empty_audit_data,
            rec.env_vars, rec.open_fds, empty_make_vars)

    data_text = pickle.dumps(data, 1) # 1 = dump as binary

    try:
        os.write(fd, data_text)
    except OSError, err:
        sys.exit(err)




description = "Concatenate multiple logs into one new log."

def usage():
    print "concat:", description
    print "NOTE: This loses audit information and make-vars info"
    print "NOTE: You can provide instmake logs via the normal options,"
    print "      (-L, --logs, --vws), or as arguments to the report."
    print "\t[OPTS] new_instmake_log [old_instmake_log ...]"
    print
    print "\t-c : Concatenate only; do not add new fake parent record"

def report(log_file_names, args):

    # Defaults
    concatenate_only = 0

    # Our options
    optstring = "c"
    longopts = []

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-c":
            concatenate_only = 1
        else:
            assert 0, "%s option not handled." % (opt,)

    # One output file
    if len(args) < 1:
        usage()
        sys.exit(0)

    new_log_name = args[0]

    # We can take log names on our command-line, too
    if len(args) > 1:
        log_file_names.extend(args[1:])

    # Open the logs so we can read their headers
    logs = []
    for log_file_name in log_file_names:
        log = LOG.LogFile(log_file_name)
        logs.append(log)

    # Create a new instmake log
    file_mode = 0664
    try:
        new_log_fd = os.open(new_log_name, os.O_CREAT|os.O_TRUNC|os.O_WRONLY,
            file_mode)
    except OSError, err:
        sys.exit("Failed to open %s: %s" % (new_log_name, err))

    LOG.WriteLatestHeader(new_log_fd, new_log_name, None, None, None)

    # Make a new, fake parent record?
    if not concatenate_only:
        new_parent_rec = FakeRec()
        new_parent_rec.pid = instmake_build.make_pid()
        new_parent_rec.retval = 0
        new_parent_rec.cwd = "/"
        new_parent_rec.times_start = (0,0,0,0,0,0)
        new_parent_rec.times_end = (0,0,0,0,0,0)
        new_parent_rec.cmdline_args = ["instmake"]

        write_rec(new_parent_rec, new_log_fd)

    # Copy each log to the new log
    for log in logs:
        # Read through the records
        while 1:
            try:
                rec = log.read_record()
                # Tie the record to the new fake parent?
                if (not concatenate_only) and (rec.ppid == None):
                    rec.ppid = new_parent_rec.pid
                write_rec(rec, new_log_fd)
            except EOFError:
                log.close()
                break

    os.close(new_log_fd)
