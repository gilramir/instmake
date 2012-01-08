# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Report multiple makes in the same directory.
"""

import sys
from instmakelib import instmake_log as LOG

description = "Over-all Build Time. Accepts multiple instmake logs."
def usage():
    print "ovtime:", description


def print_ovtime(log_file_name, print_filename):
    # Open the log file
    log = LOG.LogFile(log_file_name)

    top_rec = None

    # Read the log records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        if rec.ppid == None:
            if top_rec:
                print "Found another record with no PPID."
            top_rec = rec

    if not top_rec:
        print "No top-most record found."
        return

    print
    if print_filename:
        print "LOGFILE: ", log_file_name
    print "CWD:     ", top_rec.cwd
    print "CMDLINE: ", top_rec.cmdline
    print "RETVAL:  ", top_rec.retval
    print
    print "real   ", LOG.hms(top_rec.diff_times[rec.TimeIndex("REAL")])
    print "user   ", LOG.hms(top_rec.diff_times[rec.TimeIndex("USER")])
    print "sys    ", LOG.hms(top_rec.diff_times[rec.TimeIndex("SYS")])

def report(log_file_names, args):
    print_filename = 0

    if len(log_file_names) > 1:
        print_filename = 1

    for log_file_name in log_file_names:
        print_ovtime(log_file_name, print_filename)
        print
        print
