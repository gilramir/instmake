# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Show individual records.
"""
import getopt
import sys
from instmakelib import instmake_log as LOG

def reverse_dump(records):
    records.reverse()
    return records

def start_dump(records):
    def cmp_start(x, y):
        return cmp(x.times_start[x.REAL_TIME], y.times_start[x.REAL_TIME])

    records.sort(cmp_start)
    return records

def sort_dump(log, func):
    records = []

    # Read through the records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        records.append(rec)

    records = func(records)

    for rec in records:
        rec.Print()

def regular_dump(log):
    # Read through the records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        rec.Print()

description = "Print each record in the log."

def usage():
    print "dump:", description
    print "The instmake log has a natural order; it's sorted by end time."
    print "\t-r : reverse the instmake log (reverse sort by end time)"
    print "\t-s : sort the instmake log by start time"

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'dump' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Defaults
    reverse = 0
    sort_start = 0

    # Our options
    optstring = "rs"
    longopts = []

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-r":
            reverse = 1
        elif opt == "-s":
            sort_start = 1
        else:
            assert 0, "%s option not handled." % (opt,)

    if sort_start and reverse:
        sys.exit("Only one sort option (-r, -s) can be used at a time.")

    # Open the log file
    log = LOG.LogFile(log_file_name)

    if reverse:
        sort_dump(log, reverse_dump)
    elif sort_start:
        sort_dump(log, start_dump)
    else:
        regular_dump(log)
