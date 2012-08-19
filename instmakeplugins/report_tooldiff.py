# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Report times per tool, comparing the data from two instmake logs.
"""

import getopt
import sys
from instmakelib import instmake_log as LOG
from instmakelib import simplestats
from instmakelib import pysets

# Ways to sort
SORT_BY_BEFORE = 0
SORT_BY_AFTER = 1
SORT_BY_PCTCHANGE = 2
SORT_BY_NAME = 3

# What to show
SHOW_TOTAL = "TOTAL"
SHOW_MEAN = "MEAN"
SHOW_N = "NUMBER OF INSTANCES"
SHOW_MIN = "MINIMUM"
SHOW_MAX = "MAXIMUM"
SHOW_PCT = "PERCENT OF TOTAL BUILD"
SHOW_ALL = "SHOW ALL"

# Values for 'ascending' flag.
NOT_SET = -1
ASCENDING = 1
DESCENDING = 0

# Format strings
TIME_FMT = "%13s"
PCT_FMT = "%7.2f%%"
N_FMT = "%8d"

class StatCollection:
    """Keeps track of multiple Stat objects."""
    def __init__(self, name):
        self.real = simplestats.Stat(name)
        self.user = simplestats.Stat(name)
        self.sys = simplestats.Stat(name)
        self.cpu = simplestats.Stat(name)

    def AddReal(self, value):
        self.real.Add(value)

    def AddUser(self, value):
        self.user.Add(value)

    def AddSys(self, value):
        self.sys.Add(value)

    def AddCPU(self, value):
        self.cpu.Add(value)

    def RealTotal(self):
        return self.real.Total()

    def UserTotal(self):
        return self.user.Total()

    def SysTotal(self):
        return self.sys.Total()

    def CPUTotal(self):
        return self.cpu.Total()

    def Calculate(self, total_quad):
        (real_time, user_time, sys_time, cpu_time) = total_quad
        self.real.Calculate(real_time)
        self.user.Calculate(user_time)
        self.sys.Calculate(sys_time)
        self.sys.Calculate(cpu_time)



class StatComparison:
    """Contains two simplestats.Stat objects and knows how to compare them."""

    sort_by = SORT_BY_PCTCHANGE
    default_field = SHOW_MAX

    def __init__(self, name, stat1, stat2, show_field=None):
        self.name = name
        if show_field:
            self.field = show_field
        else:
            self.field = self.default_field

        if stat1:
            self.val1 = self.GetStatValue(stat1)
        else:
            self.val1 = 0

        if stat2:
            self.val2 = self.GetStatValue(stat2)
        else:
            self.val2 = 0

        self.pctchange = self.PctChange(self.val1, self.val2)

    def GetStatValue(self, stat):
        if self.field == SHOW_TOTAL:
            return stat.total
        elif self.field == SHOW_MEAN:
            return stat.mean
        elif self.field == SHOW_N:
            return stat.n
        elif self.field == SHOW_MIN:
            return stat.min
        elif self.field == SHOW_MAX:
            return stat.max
        elif self.field == SHOW_PCT:
            return stat.pct
        else:
            assert 0, "Unexpected field: %d" % (self.field,)

    def PctChange(self, val1, val2):
        """Returns (before, after, %-change) of any two numbers"""
        if val1 == 0:
            return None
        else:
            return 100.0 * float(val2 - val1) / float(val1) 

    def __cmp__(self, other):
        if self.sort_by == SORT_BY_BEFORE:
            return cmp(self.val1, other.val1)
        elif self.sort_by == SORT_BY_AFTER:
            return cmp(self.val2, other.val2)
        elif self.sort_by == SORT_BY_PCTCHANGE:
            if other.pctchange == None:
                return -1
            elif self.pctchange == None:
                return 1
            else:
                return cmp(self.pctchange, other.pctchange)
        elif self.sort_by == SORT_BY_NAME:
            return cmp(self.name, other.name)
        else:
            assert 0, "Unexpected sort key: %d" % (self.sort_by,)

class NullTime:
    def __init__(self):
        self.real = None
        self.user = None
        self.sys = None

class StatCollectionComparison:
    """Contains two StatCollection objects and knows how to compare them."""

    def __init__(self, name, sc1, sc2):
        self.name = name

        if sc1 == None:
            sc1 = NullTime()
        elif sc2 == None:
            sc2 = NullTime()

        self.total_real = StatComparison(name, sc1.real, sc2.real, SHOW_TOTAL)
        self.total_user = StatComparison(name, sc1.user, sc2.user, SHOW_TOTAL)
        self.total_sys = StatComparison(name, sc1.sys, sc2.sys, SHOW_TOTAL)
        self.total_cpu = StatComparison(name, sc1.cpu, sc2.cpu, SHOW_TOTAL)

        self.mean_real = StatComparison(name, sc1.real, sc2.real, SHOW_MEAN)
        self.mean_user = StatComparison(name, sc1.user, sc2.user, SHOW_MEAN)
        self.mean_sys = StatComparison(name, sc1.sys, sc2.sys, SHOW_MEAN)
        self.mean_cpu = StatComparison(name, sc1.cpu, sc2.cpu, SHOW_MEAN)

        self.max_real = StatComparison(name, sc1.real, sc2.real, SHOW_MAX)
        self.max_user = StatComparison(name, sc1.user, sc2.user, SHOW_MAX)
        self.max_sys = StatComparison(name, sc1.sys, sc2.sys, SHOW_MAX)
        self.max_cpu = StatComparison(name, sc1.cpu, sc2.cpu, SHOW_MAX)

        self.min_real = StatComparison(name, sc1.real, sc2.real, SHOW_MIN)
        self.min_user = StatComparison(name, sc1.user, sc2.user, SHOW_MIN)
        self.min_sys = StatComparison(name, sc1.sys, sc2.sys, SHOW_MIN)
        self.min_cpu = StatComparison(name, sc1.cpu, sc2.cpu, SHOW_MIN)

        self.n = StatComparison(name, sc1.real, sc2.real, SHOW_N)


    def __cmp__(self, other):
        return cmp(self.name, other.name)


description = "Compare duration per tool between two instmake logs."

def usage():
    print "tooldiff:", description
    print "    Show:",
    print "[--all|--total|--num|--min|--max|--mean|--pct] (total is default)"
    print "\t--all shows stats on all data, sorted by tool."
    print "    Sort Field: [--before|--after|--pctchange|--tool]  (pctchange is default)"
    print "\tNot valid with --all."
    print "    Sort Order:"
    print "\t-a|--ascending           (default for --tool)"
    print "\t-d|--descending          (default for all other fields)"
    print "    Time measured via: (not valid with --all, since all 3 are shown)"
    print "\t-r|--real"
    print "\t-u|--user                (default)"
    print "\t-s|--sys"
    print "\t-s|--cpu  (user + sys)"
    print "     Miscellaneous:"

def read_log(log_name, time_field, show_field):
    """Read a log file and fill a hash table, key = tool name,
    value = simplestats.Stat object."""
    # Open the log file
    log = LOG.LogFile(log_name)

    tool_stats = {}

    single_time_index = None
    real_time_index = None
    user_time_index = None
    sys_time_index = None
    cpu_time_index = None

    # Read through the records from log file
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        if not rec.tool:
            continue

        # Create an object for the tool if needed
        tool = rec.tool

        if show_field == SHOW_ALL:
            if real_time_index == None:
                real_time_index = rec.TimeIndex("REAL")
                user_time_index = rec.TimeIndex("USER")
                sys_time_index = rec.TimeIndex("SYS")
                cpu_time_index = rec.TimeIndex("CPU")

            if not tool_stats.has_key(tool):
                stat = StatCollection(tool)
                tool_stats[tool] = stat
            else:
                stat = tool_stats[tool]

            stat.AddReal(rec.diff_times[real_time_index])
            stat.AddUser(rec.diff_times[user_time_index])
            stat.AddSys(rec.diff_times[sys_time_index])
            stat.AddCPU(rec.diff_times[cpu_time_index])
        else:
            if single_time_index == None:
                single_time_index = rec.TimeIndex(time_field)

            if not tool_stats.has_key(tool):
                stat = simplestats.Stat(tool)
                tool_stats[tool] = stat
            else:
                stat = tool_stats[tool]

            time = rec.diff_times[single_time_index]
            stat.Add(time)

    # Total the 'total time' fields to get percentage.
    if show_field == SHOW_ALL:
        total_real_time = 0
        total_user_time = 0
        total_sys_time = 0
        total_cpu_time = 0

        stats = tool_stats.values()
        for stat in stats:
            total_real_time += stat.RealTotal()
            total_user_time += stat.UserTotal()
            total_sys_time += stat.SysTotal()
            total_cpu_time += stat.CPUTotal()

    
        total_time = (total_real_time, total_user_time, total_sys_time,
            total_cpu_time)

    else:
        total_time = 0
        stats = tool_stats.values()
        for stat in stats:
            total_time += stat.Total()

    return tool_stats, total_time

def report_one(scomparisons, show_field, time_field, sort_by, WIDTH_TOOL):
    tool_title = "TOOL" + " " * (WIDTH_TOOL - len("TOOL"))
    tool_dashes = "-" * WIDTH_TOOL

    # Figure out other column widths and start printing some headers
    if show_field == SHOW_PCT:
        col_width = len(PCT_FMT % 0.0)
        # Print the header
        print show_field +  ",", time_field, "TIME"
    elif show_field == SHOW_N:
        col_width = len(N_FMT % 0)
        # Print the header
        print show_field
    else:
        col_width = len(TIME_FMT % '')
        # Print the header
        print show_field, time_field, "TIME"


    before_padding = " " * (col_width - len("BEFORE"))
    after_padding = " " * (col_width - len("AFTER"))


    STAR = "(*)"
    WIDTH_STAR = len(STAR)
    WIDTH_PCTCHANGE = len("%-CHANGE")

    if sort_by == SORT_BY_NAME:
        indent = 0
    elif sort_by == SORT_BY_BEFORE:
        indent =  (WIDTH_TOOL + 1 + col_width - WIDTH_STAR)
    elif sort_by == SORT_BY_AFTER:
        indent =  (WIDTH_TOOL + 2 * (1 + col_width) - WIDTH_STAR)
    elif sort_by == SORT_BY_PCTCHANGE:
        indent =  (WIDTH_TOOL + 2 * (1 + col_width) + 1 + WIDTH_PCTCHANGE - WIDTH_STAR)

    sort_hdr = (indent * " ") + STAR

    # Print the big header
    print sort_hdr,
    print """
%s %sBEFORE %sAFTER %%-CHANGE
%s %s------ %s----- --------
""" % (tool_title, before_padding, after_padding,
    tool_dashes, before_padding, after_padding),

    # And print the data.
    for scomp in scomparisons:
        # Name
        spaces = " " * (WIDTH_TOOL - len(scomp.name))
        print "%s%s" % (scomp.name, spaces),

        if show_field == SHOW_PCT:
            print PCT_FMT % (scomp.val1,),
            print PCT_FMT % (scomp.val2,),
        elif show_field == SHOW_N:
            print N_FMT % (scomp.val1,),
            print N_FMT % (scomp.val2,),
        else:
            print TIME_FMT % (LOG.hms(scomp.val1,)),
            print TIME_FMT % (LOG.hms(scomp.val2,)),

        if scomp.pctchange == None:
            print "    NaN",
        else:
            print PCT_FMT % (scomp.pctchange,),

        # Newline.
        print

def report_value(text_fmt, text, fmt, statcoll):
        print text_fmt % text,

        if fmt == TIME_FMT:
            print TIME_FMT % (LOG.hms(statcoll.val1),),
            print TIME_FMT % (LOG.hms(statcoll.val2),),
        else:
            print fmt % (statcoll.val1,),
            print fmt % (statcoll.val2,),

        if statcoll.pctchange == None:
            print "    NaN",
        else:
            print PCT_FMT % (statcoll.pctchange,),

        # Newline.
        print

def report_all(scomparisons, WIDTH_TOOL):
    # And print the dat
    text_fmt = "%%%ds" % (WIDTH_TOOL,)
    ALL_N_FMT = "%13d"

    for scomp in scomparisons:
        tool_title = scomp.name + " " * (WIDTH_TOOL - len(scomp.name))
        tool_dashes = "-" * WIDTH_TOOL
        col_width = len(TIME_FMT % '')
        before_padding = " " * (col_width - len("BEFORE"))
        after_padding = " " * (col_width - len("AFTER"))
        print """
%s %sBEFORE %sAFTER %%-CHANGE
%s %s------ %s----- --------
""" % (tool_title, before_padding, after_padding,
        tool_dashes, before_padding, after_padding),

        report_value(text_fmt, "Total Real Time", TIME_FMT, scomp.total_real)
        report_value(text_fmt, "Total User Time", TIME_FMT, scomp.total_user)
        report_value(text_fmt, "Total Sys Time", TIME_FMT, scomp.total_sys)
        report_value(text_fmt, "Mean Real Time", TIME_FMT, scomp.mean_real)
        report_value(text_fmt, "Mean User Time", TIME_FMT, scomp.mean_user)
        report_value(text_fmt, "Mean Sys Time", TIME_FMT, scomp.mean_sys)
        report_value(text_fmt, "Max Real Time", TIME_FMT, scomp.max_real)
        report_value(text_fmt, "Max User Time", TIME_FMT, scomp.max_user)
        report_value(text_fmt, "Max Sys Time", TIME_FMT, scomp.max_sys)
        report_value(text_fmt, "Min Real Time", TIME_FMT, scomp.min_real)
        report_value(text_fmt, "Min User Time", TIME_FMT, scomp.min_user)
        report_value(text_fmt, "Min Sys Time", TIME_FMT, scomp.min_sys)
        report_value(text_fmt, "Number of Times Run", ALL_N_FMT, scomp.n)

        # Newline.
        print
        

def report(log_file_names, args):
    # We accept exactly two log file names.
    if len(log_file_names) != 2:
        sys.exit("'tooldiff' report uses exactly two log files.")
    else:
        log_name_1 = log_file_names[0]
        log_name_2 = log_file_names[1]

    # Defaults
    ascending = ASCENDING
    time_field = "USER"
    show_field = SHOW_TOTAL
    sort_by = SORT_BY_PCTCHANGE

    # We have a slew of options
    optstring = "adrusc"
    longopts = ["ascending", "descending",
        "real", "user", "sys", "cpu",
        "total", "num", "min", "max", "mean", "pct",
        "before", "after", "pctchange", "tool", "all"]

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-a" or opt == "--ascending":
            ascending = ASCENDING
        elif opt == "-d" or opt == "--descending":
            ascending = DESCENDING
        elif opt == "--before":
            sort_by = SORT_BY_BEFORE
        elif opt == "--after":
            sort_by = SORT_BY_AFTER
        elif opt == "--pctchange":
            sort_by = SORT_BY_PCTCHANGE
        elif opt == "--tool":
            sort_by = SORT_BY_NAME
        elif opt == "-r" or opt == "--real":
            time_field = "REAL"
        elif opt == "-u" or opt == "--user":
            time_field = "USER"
        elif opt == "-s" or opt == "--sys":
            time_field = "SYS"
        elif opt == "-c" or opt == "--cpu":
            time_field = "CPU"
        elif opt == "--total":
            show_field = SHOW_TOTAL
        elif opt == "--mean":
            show_field = SHOW_MEAN
        elif opt == "--num":
            show_field = SHOW_N
        elif opt == "--min":
            show_field = SHOW_MIN
        elif opt == "--max":
            show_field = SHOW_MAX
        elif opt == "--pct":
            show_field = SHOW_PCT
        elif opt == "--all":
            show_field = SHOW_ALL
        else:
            assert 0, "%s option not handled." % (opt,)

    StatComparison.default_field = show_field

    # Get the stats per tool from each log file.
    tools_1, total_time_1 = read_log(log_name_1, time_field, show_field)
    tools_2, total_time_2 = read_log(log_name_2, time_field, show_field)

    # Figure out the union of the tool names from the 2 runs.
    tool_names_set_1 = pysets.SetClass(tools_1.keys())
    tool_names_set_2 = pysets.SetClass(tools_2.keys())

    all_tool_names = tool_names_set_1.union(tool_names_set_2)

    scomparisons = []

    # Tell each object to calculate any calculated fields,
    # and make StatComparison objects.
    for tool_name in all_tool_names.items():
        # Tools 1
        if tools_1.has_key(tool_name):
            stat_1 = tools_1[tool_name]
            stat_1.Calculate(total_time_1)
        else:
            stat_1 = None

        # Tools 2
        if tools_2.has_key(tool_name):
            stat_2 = tools_2[tool_name]
            stat_2.Calculate(total_time_2)
        else:
            stat_2 = None

        if show_field == SHOW_ALL:
            scomparisons.append(StatCollectionComparison(tool_name,
                stat_1, stat_2))
        else:
            scomparisons.append(StatComparison(tool_name, stat_1, stat_2))

    # Sort
    if show_field != SHOW_ALL:
        StatComparison.sort_by = sort_by

    scomparisons.sort()

    # Maybe reverse the sort.
    if ascending == DESCENDING:
        scomparisons.reverse()

    # Determine width of "tool" column
    max_length = 0
    for scomp in scomparisons:
        length = len(scomp.name)
        max_length = max(max_length, length)
    max_length_tool_name = max(max_length, len("TOOL"))

    if show_field == SHOW_ALL:
        report_all(scomparisons, max_length_tool_name)
    else:
        report_one(scomparisons, show_field, time_field, sort_by,
            max_length_tool_name)

