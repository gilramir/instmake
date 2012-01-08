# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Report multiple makes in the same directory.
"""

import sys
import re
import os

from instmakelib import pidtree
from instmakelib import instmake_log as LOG
from instmakelib import linearmap

def show_timeline(records):
    # The linear map will keep track of concurrency for us.
    # In our case, the map is mapping time. At each time
    # interval, various jobs may be running.
    map = linearmap.LinearMap()

    # Keep the map class from doing things it normally does,
    # if the user ends up requesting the LinearMap object
    # to print a map to stdout.
    map.PrintRawOffsets()
    map.NoPrintDiff()
    map.NoPrintMapKey()
    map.IDsStartAt(1)

    for rec in records:
        #ID = map.Add(start, length, rec.pid, rec.args)
        start = rec.times_start[rec.REAL_TIME]
        length = rec.diff_times[rec.REAL_TIME]
        map.Add(start, length, rec.pid, None)

    map.PrintMap(sys.stdout)

def report_dir(dir, records):
    """Report an instance of multiple makes in a directory."""

    # Print info that is the same for all records
    print "Multiple makes in directory:", dir
    print "=" * (29 + len(dir))

    i = 1
    for rec in records:
        print "\t%3d. PID=%s PPID=%s" % (i, rec.pid, rec.ppid),
        if rec.make_target:
            print "TARGET=%s" % (rec.make_target,),

        if rec.makefile_filename:
            print "RULE=%s:%s" % (rec.makefile_filename,
                rec.makefile_lineno),

        print
        print "\t     CWD=%s" % (rec.cwd,)
        print rec.cmdline
        print

        i += 1

    print "Timeline:"
    show_timeline(records)
    print
    print

description = "Report multiple makes in a single directory."

def usage():
    print "mmake:", description

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'mmake' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Open the log file
    log = LOG.LogFile(log_file_name)

    ptree = pidtree.PIDTree()

    # Read the log records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        ptree.AddRec(rec)

    ptree.Finish()

    # Get the branch srecs from the ptree. Those are the 'make' srecs.
    srecs = ptree.BranchSRecs()
    srecs.sort()
    make_dirs = {}

    re_dash_C = re.compile(r"-C\s+(?P<chdir>\S+)")

    for srec in srecs:
        rec = srec.Rec()
        dir = rec.cwd
        # If make is called with -C, then the CWD is not
        # the dir where make runs. Figure out that working dir.
        cmd = rec.cmdline
        m = re_dash_C.search(cmd)
        if m:
#                print cmd
#                print "CWD=", rec.cwd
            chdir = m.group("chdir")
#                print "chdir=", chdir
            if os.path.isabs(chdir):
                dir = chdir
            else:
                dir = os.path.join(dir, chdir)
#                print "dir=", dir
#                print '-------------------'

        dir = os.path.normpath(dir)

        dir_recs = make_dirs.setdefault(dir, [])
        dir_recs.append(rec)

    # Report the make records by directory, if there are more
    # than one for that directory.
    for (dir, recs) in make_dirs.items():
        if len(recs) > 1:
            report_dir(dir, recs)

