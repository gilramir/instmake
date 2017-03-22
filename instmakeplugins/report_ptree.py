# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Show process tree.
"""
from instmakelib import instmake_log as LOG
import sys
from instmakelib import pidtree
import getopt

description = "Create a PID-based tree of jobs."

def usage():
    print "ptree:", description
    print "ptree [OPTS] [PID]"
    print "\t-f|--full      show full record of jobs, not just summary."
    print "\t-m|--make      show only 'make' jobs; implies --full."
    print "\t--make-targets show only 'make' job targets; implies -m but not -f."
    print "\t-r|--real      show real time when using --make-targets [default]"
    print "\t-u|--user      show user time when using --make-targets"
    print "\t-s|--sys       show sys time when using --make-targets"
    print "\t-c|--cpu       show cpu (usr+sys) time when using --make-targets"
    print "\t[PID]          start tree from PID"

def print_rec(rec, user_data, indent):
    rec.Print(sys.stdout, indent)

def print_srec(srec, indent):
    rec = srec.Rec()
    children_srecs = srec.Children()

    if children_srecs:
        spaces = "  " * indent
        children_srecs.sort()
        rec.Print(sys.stdout, indent, 0)
        # XXX this must be handled in the print plugin
#        print "%sNUM. CHILDREN: " % (spaces,), len(children_srecs)
#        print

        for child_srec in children_srecs:
            print_srec(child_srec, indent + 1)

def print_make_targets(srec, indent):
    rec = srec.Rec()
    children_srecs = srec.Children()

    if children_srecs:
        spaces = "  " * indent
        dir = rec.cwd

        if "-C" in rec.cmdline_args:
            chgdir_i = rec.cmdline_args.index("-C")
            if chgdir_i > -1 and len(rec.cmdline_args) > chgdir_i:
                dir = rec.cmdline_args[chgdir_i + 1]

        print "%s%s %s %d %s" % (spaces, dir, rec.make_target, len(children_srecs),
            LOG.hms(rec.diff_times[rec.TimeIndex(TIME_TYPE)]))
        children_srecs.sort()

        for child_srec in children_srecs:
            print_make_targets(child_srec, indent + 1)

OUTPUT_SUMMARY = 0
OUTPUT_FULL = 1
OUTPUT_MAKE = 2
OUTPUT_MAKE_TARGETS = 3

TIME_INDEX = LOG.LogRecord.REAL_TIME
TIME_TYPE = "REAL"

def report(log_file_names, args):
    global TIME_TIME
    show_entire_record = 0
    only_makes = 0
    start_pid = None
    output_type = OUTPUT_SUMMARY

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'ptree' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = "fmrusc"
    longopts = ["full", "make", "make-targets", "real", "usr", "sys", "cpu"]

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "--full" or opt == "-f":
            if output_type != OUTPUT_SUMMARY:
                sys.exit("Only one output type allowed")
            show_entire_record = 1
            output_type = OUTPUT_FULL
        elif opt == "--make" or opt == "-m":
            if output_type != OUTPUT_SUMMARY:
                sys.exit("Only one output type allowed")
            only_makes = 1
            output_type = OUTPUT_MAKE
        elif opt == "--make-targets":
            if output_type != OUTPUT_SUMMARY:
                sys.exit("Only one output type allowed")
            only_makes = 1
            output_type = OUTPUT_MAKE_TARGETS
        elif opt == "--real" or opt == "-r":
            TIME_INDEX = LOG.LogRecord.REAL_TIME
            TIME_TYPE = "REAL"
        elif opt == "--user" or opt == "-u":
            TIME_INDEX = LOG.LogRecord.USER_TIME
            TIME_TYPE = "USER"
        elif opt == "--sys" or opt == "-s":
            TIME_INDEX = LOG.LogRecord.SYS_TIME
            TIME_TYPE = "SYS"
        elif opt == "--cpu" or opt == "-c":
            TIME_INDEX = LOG.LogRecord.CPU_TIME
            TIME_TYPE = "CPU"
        else:
            assert 0, "Unexpected option %s" % (opt,)

    if len(args) == 1:
        start_pid = args[0]

    elif len(args) > 1:
        sys.exit("Only one PID can be supplied.")

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

    if start_pid:
        try:
            start_srec = ptree.GetSRec(start_pid)
        except KeyError:
            sys.exit("PID %s not found." % (start_pid,))

    if only_makes:
        if start_pid:
            srec = start_srec
        else:
            srec = ptree.TopSRec()

        if not srec:
            sys.exit("Unable to find top-most record.")

        if output_type == OUTPUT_MAKE:
            print_srec(srec, 0)
        elif output_type == OUTPUT_MAKE_TARGETS:
            print "Makes and their targets"
            print
            print "Directory        Target        # Child Processes     ", TIME_TYPE, "time"
            print
            print_make_targets(srec, 0)
        else:
            assert 0, "Unexpected output_type: " + output_type


    else:
        if show_entire_record:
            if start_pid:
                start_srec.Walk(print_rec)
            else:
                ptree.Walk(print_rec)
        else:
            if start_pid:
                start_srec.PrintTree()
            else:
                ptree.Print()

