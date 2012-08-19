# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Show concurrent processes for a single instmake log.
"""

# The Python libraries that we need
from instmakelib import instmake_log as LOG
import sys
import getopt
from instmakelib import concurrency

description = "Show concurrent-process stats."

def usage():
    print "conprocs:", description
    print "     [--non-make|--only-make|--all]: DEFAULT=--non-make"
    print "     [--timeline] show process timeline (always shows ALL processes)"
    print "     [--tools] summarize tools in use during each -j chunk."
    print "     [--procs] show processes during each -j chunk."
    print "     [--procs-j=N] show processes during -jN chunk."

def report_the_procs(conprocs, jobslot):
    print "=" * 80
    pids = conprocs.PIDsForJ(jobslot)
    for pid in pids:
        conprocs.Rec(pid).Print()

def report_the_tools(conprocs, jobslot):
    tools = conprocs.ToolsForJ(jobslot)
#    print "NUMTOOLS", len(tools)
    stats = {}
    for tool in tools:
        if stats.has_key(tool):
            stats[tool] += 1
        else:
            stats[tool] = 1

    sorted_tools = stats.keys()
    sorted_tools.sort()
    i = 1
    for tool in sorted_tools:
        num = stats[tool]
        ext = "s"
        if num == 1:
            ext = ""
        print "%d. %-30s %6d time%s" % (i, tool, num, ext)
        i += 1

    print

def report(log_file_names, args):
    mode = concurrency.NON_MAKE
    show_timeline = 0
    show_tools = 0
    show_procs = 0
    show_procs_j = []

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'conprocs' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = ""
    longopts = ["non-make", "only-make", "all", "timeline", "tools", "procs",
        "procs-j="]

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "--non-make":
            mode = concurrency.NON_MAKE
        elif opt == "--only-make":
            mode = concurrency.ONLY_MAKE
        elif opt == "--all":
            mode = concurrency.ALL
        elif opt == "--timeline":
            show_timeline = 1
        elif opt == "--tools":
            show_tools = 1
        elif opt == "--procs":
            show_procs = 1
        elif opt == "--procs-j":
            try:
                show_procs_j.append(int(arg))
            except ValueError:
                sys.exit("--procs-j accepts an integer value")
        else:
            assert 0, "Unexpected option %s" % (opt,)

    keep_recs_flag = show_procs or show_procs_j

    conprocs = concurrency.Concurrency(log_file_name, mode,
        show_timeline, show_tools, keep_recs=keep_recs_flag)

    # Add an extra title line.
    if mode == concurrency.NON_MAKE:
        title = "Concurrent Non-Make Processes During Build"
    elif mode == concurrency.ONLY_MAKE:
        title = "Concurrent Make Processes During Build"
    elif mode == concurrency.ALL:
        title = "Concurrent Processes (Make and Non-Make) During Build"
    else:
        assert 0, "Mode %s not expected" % (mode,)

    print title
    top_rec = conprocs.TopRecord()
    ovtime = top_rec.diff_times[top_rec.REAL_TIME]

    # Find the total number of processes.
    unique_ids = {}
    for jobslot in range(conprocs.NumJobSlots()):
        for ID in conprocs.IDsForJ(jobslot):
            unique_ids[ID] = None

    tot_procs = len(unique_ids.keys())
    del unique_ids

    print
    print "Note: SUM(NUM PROCS) > Total Processes Considered, and"
    print "      SUM(%PROCS) > 100% because the same process"
    print "      can be running when NUMJOBS = N, NUMJOBS = N-1, etc."
    print
    print "Note: SUM(%TIME) == 100% and SUM(REAL TIME) = Overall Real Time"
    print
    print "Note: Processes with 0.000 real time not considered."
    print
    print "Overall Time:"
    print "\treal   ", LOG.hms(top_rec.diff_times[top_rec.REAL_TIME])
    print "\tuser   ", LOG.hms(top_rec.diff_times[top_rec.USER_TIME])
    print "\tsys    ", LOG.hms(top_rec.diff_times[top_rec.SYS_TIME])
    print
    print "Total Processes Considered:", tot_procs
    print
    print "-j SLOT  NUM PROCS    %PROCS       REAL TIME   %TIME"

    for (jobslot, pct_duration) in conprocs.Results():
        jobslot_duration = LOG.hms(ovtime * pct_duration / 100.0)
        num_procs = len(conprocs.PIDsForJ(jobslot))
        pct_procs = 100.0 * float(num_procs) / float(tot_procs)

        print "     %2d     %6d   %6.2f%% %15s %6.2f%%" % \
            (jobslot, num_procs, pct_procs, jobslot_duration, pct_duration)

        if show_tools:
            report_the_tools(conprocs, jobslot)

        if show_procs:
            report_the_procs(conprocs, jobslot)
        elif jobslot in show_procs_j:
            report_the_procs(conprocs, jobslot)


    if show_timeline:
        print
        print "Timeline"
        print
        conprocs.PrintMap(sys.stdout)
