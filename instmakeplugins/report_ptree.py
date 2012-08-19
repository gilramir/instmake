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
    print "\t-m|--make      shows only 'make' jobs; implies --full."
    print "\t--make-targets shows only 'make' job targets."
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
        print "%sNUM. CHILDREN: " % (spaces,), len(children_srecs)
        print

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
            LOG.hms(rec.diff_times[rec.REAL_TIME]))
        children_srecs.sort()

        for child_srec in children_srecs:
            print_make_targets(child_srec, indent + 1)

OUTPUT_SUMMARY = 0
OUTPUT_FULL = 1
OUTPUT_MAKE = 2
OUTPUT_MAKE_TARGETS = 3

def report(log_file_names, args):
    show_entire_record = 0
    only_makes = 0
    start_pid = None
    output_type = OUTPUT_SUMMARY

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'ptree' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = "fm"
    longopts = ["full", "make", "make-targets"]

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "--full" or opt == "-f":
            show_entire_record = 1
            output_type = OUTPUT_FULL
        elif opt == "--make" or opt == "-m":
            only_makes = 1
            output_type = OUTPUT_MAKE
        elif opt == "--make-targets":
            only_makes = 1
            output_type = OUTPUT_MAKE_TARGETS
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
            print_make_targets(srec, 0)
        else:
            assert 0


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

