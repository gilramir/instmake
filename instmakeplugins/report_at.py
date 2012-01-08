# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Shows procs running at a certain time.
"""

import sys
import getopt
from instmakelib import instmake_log as LOG
from instmakelib import imlib
from instmakelib import parentfinderclass


ALL_JOBS = 0
NON_MAKE = 1
ONLY_MAKE = 2

description = "Show procs running at a certain time."

def usage():
    print "at:", description
    print "  One of:"
    print "\t[-t REAL_TIME]    Show procs running at REAL_TIME"
    print "\t[-t REAL_TIME -t REAL_TIME]  Show procs running between REAL_TIMEs"
    print "\t[--last]          Show procs running at any time during last proc"
    print "\t[--last-start]    Show procs running at the start time of the last proc"
    print "\t[--last-end]      Show procs running at the end time of the last proc"
    print "\t[-p|--pid PID]    Show procs running at any time during run of PID"
    print "\t[--pid-start PID] Show procs running at start of PID"
    print "\t[--pid-end PID]   Show procs running at end of PID"
    print "  Or both of:"
    print "\t[--from REAL_TIME]"
    print "\t[--to REAL_TIME]"
    print "  At any time:"
    print "\t[--non-make]"
    print "\t[--only-make]"

def report(log_file_names, args):
    time_start = None
    time_end = None

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'at' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = "t:p:"
    longopts = ["last", "last-start", "last-end", "pid=", "pid-start=",
        "pid-end=", "from=", "to=", "non-make", "only-make" ]
    
    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    job_types = ALL_JOBS

    for opt, arg in opts:
        if opt == "-t":
            if time_start == None:
                try:
                    time_start = float(arg)
                except ValueError:
                    sys.exit("%s is not a number." % (arg,))
            elif time_end == None:
                try:
                    time_end = float(arg)
                except ValueError:
                    sys.exit("%s is not a number." % (arg,))
            else:
                sys.exit("Too many -t options given.")

        elif opt == "--last":
            rec = find_last_proc(log_file_name)
            time_start = rec.times_start[rec.REAL_TIME]
            time_end = rec.times_end[rec.REAL_TIME]

        elif opt == "--last-start":
            rec = find_last_proc(log_file_name)
            time_start = rec.times_start[rec.REAL_TIME]

        elif opt == "--last-end":
            rec = find_last_proc(log_file_name)
            time_start = rec.times_end[rec.REAL_TIME]

        elif opt == "-p" or opt == "--pid":
            rec = find_pid(log_file_name, arg)
            time_start = rec.times_start[rec.REAL_TIME]
            time_end = rec.times_end[rec.REAL_TIME]

        elif opt == "--pid-start":
            rec = find_pid(log_file_name, arg)
            time_start = rec.times_start[rec.REAL_TIME]

        elif opt == "--pid-end":
            rec = find_pid(log_file_name, arg)
            time_start = rec.times_end[rec.REAL_TIME]

        elif opt == "--from":
            time_start = float(arg)

        elif opt == "--to":
            time_end = float(arg)

        elif opt == "--non-make":
            job_types = NON_MAKE

        elif opt == "--only-make":
            job_types = ONLY_MAKE

        else:
            sys.exit("Unhandled option: %s" % (opt,))

    if args:
        print "No arguments allowed; only options."
        usage()
        sys.exit(1)

    if time_start and time_end:
        if time_start > time_end:
            (time_start, time_end) = (time_end, time_start)

    find_recs(log_file_name, time_start, time_end, job_types)

def find_last_proc(log_file_name):
    # Open the log file
    log = LOG.LogFile(log_file_name)

    newest_rec = None
    newest_rec_start_time = None

    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        if newest_rec == None:
            newest_rec = rec
            newest_rec_start_time = rec.times_start[rec.REAL_TIME]
        else:
            if rec.times_start[rec.REAL_TIME] > newest_rec_start_time:
                newest_rec = rec
                newest_rec_start_time = rec.times_start[rec.REAL_TIME]

    if newest_rec:
        return newest_rec
    else:
        sys.exit("No records found.")

def find_pid(log_file_name, pid):
    # Open the log file
    log = LOG.LogFile(log_file_name)

    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        if rec.pid == pid:
            log.close()
            return rec

    sys.exit("PID %s not found." % (pid,))

def find_recs(log_file_name, time_start, time_end, job_types):
    # Open the log file
    log = LOG.LogFile(log_file_name)

    recs = []
    if job_types != ALL_JOBS:
        parentfinder = parentfinderclass.ParentFinder()

    # Looking at a single timestamp?
    if time_end == None:
        while 1:
            try:
                rec = log.read_record()
            except EOFError:
                log.close()
                break

            ok = 1
            if job_types != ALL_JOBS:
                parentfinder.Record(rec)

            if job_types == NON_MAKE:
                ok = not parentfinder.IsParent(rec)
            elif job_types == ONLY_MAKE:
                ok = parentfinder.IsParent(rec)

            if ok and rec.times_start[rec.REAL_TIME] <= time_start and \
                    rec.times_end[rec.REAL_TIME] >= time_start:
                recs.append(rec)

    # Looking at a timestamp range?
    else:
        while 1:
            try:
                rec = log.read_record()
            except EOFError:
                log.close()
                break

            ok = 1
            if job_types != ALL_JOBS:
                parentfinder.Record(rec)

            if job_types == NON_MAKE:
                ok = not parentfinder.IsParent(rec)
            elif job_types == ONLY_MAKE:
                ok = parentfinder.IsParent(rec)

            if ok and ((rec.times_start[rec.REAL_TIME] <= time_start and \
                    rec.times_end[rec.REAL_TIME] >= time_start) or \
                (rec.times_start[rec.REAL_TIME] <= time_end and \
                rec.times_end[rec.REAL_TIME] >= time_end) or \
                (time_start <= rec.times_start[rec.REAL_TIME] <= time_end and \
                time_start <= rec.times_end[rec.REAL_TIME] <= time_end)):

                recs.append(rec)

    if recs:
        recs.sort(imlib.cmp_real_time_start)
        for rec in recs:
            rec.Print()

