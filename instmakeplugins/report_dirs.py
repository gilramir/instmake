# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Report all dirs used in build.
"""

import sys

from instmakelib import instmake_log as LOG

description = "Report directories used in build."

def usage():
    print "dirs:", description

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'mmake' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Open the log file
    log = LOG.LogFile(log_file_name)

    dirs = {}

    # Read the log records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        if not dirs.has_key(rec.cwd):
            dirs[rec.cwd] = 1
        else:
            dirs[rec.cwd] += 1

    dirnames = dirs.keys()
    dirnames.sort()

    maxnum = max(dirs.values())
    width = len(str(maxnum))
    fmt = "%%%sd %%s" % (width,)

    for dirname in dirnames:
        print fmt % (dirs[dirname], dirname)

