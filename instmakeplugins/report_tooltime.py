# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Report times per tool. The tool is the program being
invoked by make.
"""
from __future__ import nested_scopes

import getopt
import sys
from instmakelib import simplestats
from instmakelib import instmake_log as LOG
from instmakelib import pidtree


description = "Show duration per tool."

def usage():
    print "tooltime:", description
    print "    [--no-wrap]"
    print "    Sort:",
    print "[--tool|--total|--num|--min|--max|--mean|--pct] (max is default)"
    print "\t-a|--ascending           (default for --tool)"
    print "\t-d|--descending          (default for all other fields)"
    print "    Time measured via:"
    print "\t-r|--real"
    print "\t-u|--user"
    print "\t-s|--sys"
    print "\t-c|--cpu (default, user + sys)"
    print "    Records:"
    print "\t--non-make [default]"
    print "\t--all"
    print "\t--only-make"

NON_MAKE = 0
ALL = 1
ONLY_MAKE = 2

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'tooltime' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Defaults
    ascending = -1
    default_ascending = 0
    time_field = "CPU"
    sort_field = simplestats.SORT_BY_MAX
    wrap = 1
    record_type = NON_MAKE

    # We have a slew of options
    optstring = "adrusc"
    longopts = ["ascending", "descending",
        "real", "user", "sys", "cpu",
        "non-make", "all", "only-make",
        "tool", "total", "num", "min", "max", "mean", "pct", "no-wrap"]

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-a" or opt == "--ascending":
            ascending = 1
        elif opt == "-d" or opt == "--descending":
            ascending = 0
        elif opt == "-r" or opt == "--real":
            time_field = "REAL"
        elif opt == "-u" or opt == "--user":
            time_field = "USER"
        elif opt == "-s" or opt == "--sys":
            time_field = "SYS"
        elif opt == "-c" or opt == "--cpu":
            time_field = "CPU"
        elif opt == "--tool":
            sort_field = simplestats.SORT_BY_NAME
            default_ascending = 1
        elif opt == "--total":
            sort_field = simplestats.SORT_BY_TOTAL
        elif opt == "--mean":
            sort_field = simplestats.SORT_BY_MEAN
        elif opt == "--num":
            sort_field = simplestats.SORT_BY_N
        elif opt == "--min":
            sort_field = simplestats.SORT_BY_MIN
        elif opt == "--max":
            sort_field = simplestats.SORT_BY_MAX
        elif opt == "--pct":
            sort_field = simplestats.SORT_BY_PCT
        elif opt == "--no-wrap":
            wrap = 0
        elif opt == "--non-make":
            record_type = NON_MAKE
        elif opt == "--all":
            record_type = ALL
        elif opt == "--only-make":
            record_type = ONLY_MAKE
        else:
            assert 0, "%s option not handled." % (opt,)

    if ascending == -1:
        ascending = default_ascending

    # If filtering record types, then read through the
    # instmake log one time to determine record type.
    if record_type != ALL:
        log = LOG.LogFile(log_file_name)
        ptree = pidtree.PIDTreeLight()
        while 1:
            try:
                rec = log.read_record()
            except EOFError:
                log.close()
                break
            ptree.AddRec(rec)

            make_pids = ptree.BranchPIDs()
    else:
        make_pids = None

    # Open the log file
    log = LOG.LogFile(log_file_name)
    tools = {}
    time_index = None

    # Read through the records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        if not rec.tool:
            continue

        if record_type == ONLY_MAKE:
            if not rec.pid in make_pids:
                continue
        elif record_type == NON_MAKE:
            if rec.pid in make_pids:
                continue

        if time_index == None:
            time_index = rec.TimeIndex(time_field)

        # Create an object for the tool if needed
        tool = tools.setdefault(rec.tool, simplestats.Stat(rec.tool))
        time = rec.diff_times[time_index]
        tool.Add(time)

    # Get the stats
    stats = tools.values()

    # Total the 'total time' fields to get percentage.
    total_time = 0
    for stat in stats:
        total_time += stat.Total()

    # Tell each object to calculate any calculated fields.
    for stat in stats:
        stat.Calculate(total_time)

    # Sort
    simplestats.Stat.sort_by = sort_field
    stats.sort()

    # Maybe reverse the sort.
    if not ascending:
        stats.reverse()

    # Determine width of "tool" column
    if wrap:
        WIDTH_TOOL = 25
    else:
        max_length = 0
        for stat in stats:
            length = len(stat.name)
            max_length = max(max_length, length)
        WIDTH_TOOL = max(max_length, len("TOOL"))

    tool_spaces = " " * WIDTH_TOOL
    tool_title = "TOOL" + " " * (WIDTH_TOOL - len("TOOL"))
    tool_dashes = "-" * WIDTH_TOOL

    TIME_FORMAT = "%13s"
    PCT_FMT = "%6.2f%%"

    # Create the first line of the header, the star showing which
    # column is the sort column.
    WIDTH_N = 8
    WIDTH_TIME = 13
    WIDTH_PCT = 7

    WIDTH_STAR = 3

    if sort_field == simplestats.SORT_BY_NAME:
        indent = 0

    elif sort_field == simplestats.SORT_BY_TOTAL:
        indent =  (WIDTH_TOOL + 1 + WIDTH_N + 1 + WIDTH_TIME - WIDTH_STAR)

    elif sort_field == simplestats.SORT_BY_MEAN:
        indent =  (WIDTH_TOOL + 1 + WIDTH_N + 4 * (WIDTH_TIME + 1) + \
            WIDTH_PCT + 1 - WIDTH_STAR)

    elif sort_field == simplestats.SORT_BY_N:
        indent =  (WIDTH_TOOL + 1 + WIDTH_N - WIDTH_STAR)

    elif sort_field == simplestats.SORT_BY_MIN:
        indent =  (WIDTH_TOOL + 1 + WIDTH_N + 2 * (WIDTH_TIME + 1) + \
            WIDTH_PCT + 1 - WIDTH_STAR)

    elif sort_field == simplestats.SORT_BY_MAX:
        indent =  (WIDTH_TOOL + 1 + WIDTH_N + 3 * (WIDTH_TIME + 1) + \
            WIDTH_PCT + 1 - WIDTH_STAR)

    elif sort_field == simplestats.SORT_BY_PCT:
        indent =  (WIDTH_TOOL + 1 + WIDTH_N + 1+ WIDTH_TIME + 1 + \
            WIDTH_PCT - WIDTH_STAR)

    sort_hdr = (indent * " ") + "(*)"

    grand_n = 0
    grand_total = 0.0
    # Print the header
    print time_field, "TIME,",
    if record_type == ALL:
        print "Make and Non-Make Records"
    elif record_type == NON_MAKE:
        print "Non-Make Records"
    elif record_type == ONLY_MAKE:
        print "Only Make Records"
    else:
        sys.exit("Unknown record_type %d." % (record_type,))

    print sort_hdr,
    print """
%s    TIMES         TOTAL   %% TOT           MIN           MAX          MEAN
%s      RUN          TIME    TIME          TIME          TIME          TIME
%s -------- ------------- ------- ------------- ------------- -------------
""" % (tool_spaces, tool_title, tool_dashes),

    def print_name(name):
        if len(name) > WIDTH_TOOL:
            print name
            print  " " * (WIDTH_TOOL),
        else:
            spaces = " " * (WIDTH_TOOL - len(name))
            print "%s%s" % (name, spaces),

    # And print the data.
    for stat in stats:
        # Name
        print_name(stat.name)

        # N
        grand_n += stat.n
        print "%8d" % (stat.n,),

        # Times and percent
        grand_total += stat.total
        print TIME_FORMAT % (LOG.hms(stat.total),),
        print PCT_FMT % (stat.pct,),
        print TIME_FORMAT % (LOG.hms(stat.min),),
        print TIME_FORMAT % (LOG.hms(stat.max),),
        print TIME_FORMAT % (LOG.hms(stat.mean),),

        # Newline.
        print

    # Newline.
    print
    print_name("TOTAL")
    print "%8d" % (grand_n,),
    print TIME_FORMAT % (LOG.hms(grand_total),),
    print
