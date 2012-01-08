# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Show the pregression of the build in terms of time spent
working versus time spent waiting.
"""
import sys
import getopt
from instmakelib import instmake_log as LOG

description = "Show time spent waiting (real - cpu time) per job."

# Field indices in our record
PID = 0
START = 1
END = 2
REAL = 3
CPU = 4
TOOL = 5

JOB_START = 0
JOB_END = 1

min_threshhold = None

def usage():
    print "parts: NUM_PARTS", description
    print "\t-s|--start     Sort jobs by start time (default)."
    print "\t-e|--end       Sort jobs by end time."
    print "\t--min SECS     Only consider jobs that took SECS seconds."

def report(log_file_names, args):
    global min_threshhold
    sort_type = JOB_START

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'parts' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Options
    optstring = "se"
    longopts = ["start", "end", "min="]
    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-s" or opt == "--start":
            job_type = JOB_START
        elif opt == "-e" or opt == "--end":
            job_type = JOB_END
        elif opt == "--min":
            try:
                min_threshhold = float(arg)
            except ValueError:
                sys.exit("'%s' is not a floating point number." % (arg,))
        else:
            sys.exit("Unhandled option: %s" % (opt,))

    if len(args) != 0:
        sys.exit("No arguments are accepted.")

    # Open the log file
    log = LOG.LogFile(log_file_name)

    records = []
    ppids = {}

    # DEfine the function that will help us sort records.
    if sort_type == JOB_START:
        sort_func = lambda rec1, rec2: \
                        cmp(rec1[START], rec2[START])

    elif sort_type == JOB_END:
        sort_func = lambda rec1, rec2: \
                        cmp(rec1[END], rec2[END])
    else:
        sys.exit("Unexpected value for sort_type: %s" % (sort_type,))

    # Read all records.
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        # Record the PPID before we throw this out due to the threshhold
        ppids[rec.ppid] = None

        if min_threshhold != None:
            if rec.diff_times[rec.REAL_TIME] < min_threshhold:
                continue

        records.append( (rec.pid,
            rec.times_start[rec.REAL_TIME],
            rec.times_end[rec.REAL_TIME],
            rec.diff_times[rec.REAL_TIME],
            rec.diff_times[rec.CPU_TIME],
            rec.tool) )


    # Remove parent-processes from records
    records = [rec for rec in records
                    if not ppids.has_key(rec[PID])]

    # Sort the jobs
    records.sort(sort_func)

    # Report each job
    fmt = "%-10s %12s %12s %12s %9s %s"
    print fmt % ("PID", "CPU TIME", "REAL TIME", "WAITING", "WAIT %", "TOOL")
    for rec in records:
        pid = rec[PID]
        cpu = rec[CPU]
        real = rec[REAL]
        tool = rec[TOOL]
        cpu_string = LOG.hms(cpu)
        real_string = LOG.hms(real)

        # Small floating point differences will return a tiny
        # negative number. We don't want that to show up in the
        # report, so we just change the number to 0.0
        waiting = max(real - cpu, 0.0)
        wait_string = LOG.hms(waiting)

        if real == 0:
            pct_string = "%9s" % ("NaN",)
        else:
            pct_string = "%8.4f%%" % (100.0 * waiting / real,)

        print fmt % \
                (pid, cpu_string, real_string, wait_string, pct_string, tool)
