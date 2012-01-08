# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Show individual records, chosen by PID.
"""
import sys
from instmakelib import instmake_log as LOG

description = "Show records of specified PIDs."

def usage():
    print "pid:", description

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'pid' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Open the log file
    log = LOG.LogFile(log_file_name)

    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        for pid in args:
            if rec.pid == pid:
                rec.Print()
                args.remove(pid)
                break
