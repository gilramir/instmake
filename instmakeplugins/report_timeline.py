# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Show the timeline
"""

# The Python libraries that we need
import sys
from instmakelib import concurrency
import getopt

description = "Show process timeline."
def usage():
    print "timeline:", description
    print "\t[PID ...] show timeline only for listed PIDs"
    print "\t(same as 'conprocs --timeline', but doesn't require a top-most record)"

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'timeline' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = ""
    longopts = []
    
    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    if args:
        pids = args
        contype = concurrency.SPECIFIC_PIDS
    else:
        pids = []
        contype = concurrency.ALL

    SAVE_ARGS=1
    SAVE_TOOLS=0
    REQUIRE_TOP_REC=0

    conprocs = concurrency.Concurrency(log_file_name, contype,
        SAVE_ARGS, SAVE_TOOLS, require_top_rec=REQUIRE_TOP_REC,
        only_pids=pids)

    conprocs.PrintMap(sys.stdout)
