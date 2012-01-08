# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Finds bottlenecks in a build.
"""

# The Python libraries that we need
from instmakelib import instmake_log as LOG
import sys
import getopt
from instmakelib import parentfinderclass
from instmakelib import timelineclass

from math import sqrt

description = "Finds bottlenecks in a build."

def usage():
    print "bottleneck: NUM_PARTS", description


def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'bottleneck' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = ""
    longopts = []

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    if len(args) != 1:
        usage()
        sys.exit(1)

    try:
        num_parts = int(args[0])
    except ValueError:
        print >> sys.stderr, "NUM_PARTS should be a number."
        usage()
        sys.exit(1)

    # Open the log file
    log = LOG.LogFile(log_file_name)
    parentfinder = parentfinderclass.ParentFinder()
    timeline = timelineclass.Timeline()

    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        parentfinder.Record(rec)

        if not parentfinder.IsParent(rec):
            timeline.Record(rec)

    timeline.Finalize()

    run_report(timeline, num_parts)

class DescriptiveStatistics:
    def __init__(self):
        self.mean_tmp_sum = 0
        self.ss_tmp_sum = 0

        self.mean = 0
        self.n1 = 0
        self.std_dev = 0
        self.n2 = 0


    def FirstPass(self, num):
        self.mean_tmp_sum += num
        self.n1 += 1

    def Mean(self):
        self.mean = float(self.mean_tmp_sum) / self.n1
        return self.mean

    def SecondPass(self, num):
        # The square of the difference of the number
        # and the overall mean
        self.ss_tmp_sum += (self.mean - num) ** 2
        self.n2 += 1

    def StandardDeviation(self):
        if self.n2 != self.n1:
            raise ValueError("FirstPass N=%d, SecondPass N=%d" % \
                    (self.n1, self.n2))

        variance = self.ss_tmp_sum / self.n2 - 1
        self.std_dev = sqrt(variance)
        return self.std_dev


def run_report(timeline, parts):
    means = timeline.MeanRecs(parts)

    statistics = DescriptiveStatistics()

    for (start_time, end_time, mean_n) in means:
        statistics.FirstPass(mean_n)

    overall_mean = statistics.Mean()

    for (start_time, end_time, mean_n) in means:
        statistics.SecondPass(mean_n)

    std_dev = statistics.StandardDeviation()
    bottleneck_limit = overall_mean - (1.64 * std_dev)

    wall_duration = timeline.FinishTime() - timeline.StartTime()
    sample_duration = wall_duration / len(means)
    print "JOB INFORMATION"
    print "Num records:        ", timeline.NumRecords()
    print "Start time:         ", timeline.StartTime()
    print "Finish time:        ", timeline.FinishTime()
    print "Wall-time duration: ", wall_duration, LOG.hms(wall_duration)
    print "Cumulative duration:", timeline.TotalTime(), \
            LOG.hms(timeline.TotalTime())
    print
    print "HISTOGRAM INFORMATION"
    print "Num samples:        ", len(means)
    print "Sample duration:    ", sample_duration, LOG.hms(sample_duration)
    print "Overall mean:       ", overall_mean
    print "Std. Dev:           ", std_dev
    print "Bottleneck limit:   ", bottleneck_limit
    print 
    print "   #       START          FINISH       # JOBS BOTTLENECK?"  

    i = 0
    for (start_time, end_time, mean_n) in means:
        i += 1
        if mean_n <= bottleneck_limit:
            bottleneck = "*"
        else:
            bottleneck = " "
        print "%4d %14.2f  %14.2f  %8.2f %s" % (i,
                start_time, end_time, mean_n, bottleneck)
    print
