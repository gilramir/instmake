# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Stats on command-line length
"""
import getopt
import sys
from instmakelib import instmake_log as LOG


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
    print "clilen:", description
    print "\t-a : ascending sort order"
    print "\t-d : descending sort order (default)"
    print "\t-n : sort by number of args"
    print "\t-t : sort by total length (default)"

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'clilen' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    TOTAL = 0
    NUM = 1

    ASCENDING = 0
    DESCENDING = 1

    # Defaults
    sort_by = TOTAL
    sort_order = DESCENDING

    # Our options
    optstring = "adnt"
    longopts = []

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-a":
            sort_order = ASCENDING
        elif opt == "-d":
            sort_order = DESCENDING
        elif opt == "-n":
            sort_by = NUM
        elif opt == "-t":
            sort_by = TOTAL
        else:
            assert 0, "%s option not handled." % (opt,)

    # Open the log file
    log = LOG.LogFile(log_file_name)

    # Read through the records
    records = []
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        records.append(rec)

    if sort_by == TOTAL:
        records.sort(by_total)
    else:
        records.sort(by_num)

    if sort_order == DESCENDING:
        records.reverse()

    for rec in records:
        rec.Print(sys.stdout, 0, 0)
        print "CMDLINE LENGTH:", len(rec.cmdline)
        print "# CMDLINE ARGS:", len(rec.cmdline_args)
        print

def by_total(rec_a, rec_b):
    return cmp(len(rec_a.cmdline), len(rec_b.cmdline))

def by_num(rec_a, rec_b):
    return cmp(len(rec_a.cmdline_args), len(rec_b.cmdline_args))
