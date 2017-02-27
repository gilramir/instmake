# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Simply sort records by duration, using any of the times
that the user wants (user, sys, real).
"""
from __future__ import nested_scopes

import getopt
import sys
from instmakelib import instmake_log as LOG

# Guard against old versions of Python
try:
    True
except NameError:
    False = 0
    True = not False

def make_sort_func(sort_index, first_rec):
    """Returns a function which can sort on any time field. Requires
    an example record so the proper time index can be found for this type
    of instmake log (earlier versions had different time storage layouts)."""
    time_index = first_rec.TimeIndex(sort_index)
    return lambda rec_a, rec_b : \
        cmp(rec_a.diff_times[time_index], rec_b.diff_times[time_index])

description = "Show all jobs, sorted by duration"

def usage():
    print "duration:", description
    print "\t-a|--ascending           (default)"
    print "\t-d|--descending"
    print "\t-r|--real"
    print "\t-u|--user"
    print "\t-s|--sys"
    print "\t-c|--cpu     (default, user + sys)"
    print "\t--non-make   (show only non-make processes)"
    print "\t--make       (show only make processes)"

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'duplicate' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Defaults
    ascending = 1
    sort_field = "CPU"
    include_make_procs = True
    only_make_procs = False

    # We have a slew of options
    optstring = "adrusc"
    longopts = ["ascending", "descending",
        "real", "user", "sys", "cpu", "non-make", "make"]

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-a" or opt == "--ascending":
            pass
        elif opt == "-d" or opt == "--descending":
            ascending = 0
        elif opt == "-r" or opt == "--real":
            sort_field = "REAL"
        elif opt == "-u" or opt == "--user":
            sort_field = "USER"
        elif opt == "-s" or opt == "--sys":
            sort_field = "SYS"
        elif opt == "-c" or opt == "--cpu":
            sort_field = "CPU"
        elif opt == "--make":
            only_make_procs = True
        elif opt == "--non-make":
            include_make_procs = False
        else:
            assert 0, "%s option not handled." % (opt,)

    # Open the log file
    log = LOG.LogFile(log_file_name)

    records = []
    ppids = {}

    # Read through the records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        # Create an object for each record and add it to our array
        records.append(rec)
        ppids[rec.ppid] = None
#        ppids.setdefault(rec.ppid, []).append(rec.pid)

    if not records:
        return

    if only_make_procs:
        # Remove chlid-processes from records
        records = [rec for rec in records
                    if ppids.has_key(rec.pid)]

    if not include_make_procs:
        # Remove parent-processes from records
        records = [rec for rec in records
                    if not ppids.has_key(rec.pid)]

    # Sort!
    sort_func = make_sort_func(sort_field, records[0])
    records.sort(sort_func)

    # Maybe reverse the sort.
    if not ascending:
        records.reverse()

    # And dump the data.
    for rec in records:
        rec.Print()
        print
