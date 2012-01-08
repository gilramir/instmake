# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Partition the build into summaries per chunk-of-time.
"""
import sys
import getopt
from instmakelib import instmake_log as LOG

description = "Partition the build into chunks based on time."

START = 0
END = 1
TOOL = 2
PID = 3

JOB_START = 0
JOB_END = 1
JOB_DURATION = 2

def usage():
    print "parts: NUM_PARTS", description
    print "\t-s|--start     Jobs that start during time period."
    print "\t-e|--end       Jobs that end during time period."
    print "\t-d|--duration  Jobs that exist during time period (default)."

def report(log_file_names, args):
    job_type = JOB_DURATION

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'parts' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Options
    optstring = "sed"
    longopts = ["start", "end", "duration"]
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
        elif opt == "-d" or opt == "--duration":
            job_type = JOB_DURATION
        else:
            sys.exit("Unhandled option: %s" % (opt,))

    if len(args) != 1:
        sys.exit("Need number of parts.")

    try:
        numparts = int(args[0])
    except ValueError:
        sys.exit("'parts' requires an integer argument.")

    if numparts <= 0:
        sys.exit("'parts' requires an argument > 0.")

    # Open the log file
    log = LOG.LogFile(log_file_name)

    records = []
    ppids = {}

    # Determine the function that will help us collate records.
    # 'job_func_any' is used to find the jobs for any time chunk.
    # 'job_func_end' is used to find the jobs in the last time chunk only.
    if job_type == JOB_START:
        # Job starts between start/end
        job_func_any = lambda rec, start, end: \
                        rec[START] >= start and rec[START] < end
        job_func_end = lambda rec, start, end: \
                        rec[START] >= start and rec[START] <= end

    elif job_type == JOB_END:
        # Job ends between start/end
        job_func_any = lambda rec, start, end: \
                        rec[END] >= start and rec[END] < end
        job_func_end = lambda rec, start, end: \
                        rec[END] >= start and rec[END] <= end

    elif job_type == JOB_DURATION:
        # Job exists somewhwere between start/end
        job_func_any = lambda rec, start, end: \
                        (rec[START] >= start and rec[START] < end) or \
                        (rec[END] >= start and rec[END] < end) or \
                        (rec[START] <= start and rec[END] >= end)
        # Special case; since we know we're looking at the last chunk
        # of time, we only have to check that a job *ended* during this
        # chunk. All jobs must end in this chunk since there are no
        # more chunks for them to end in.
        job_func_end = lambda rec, start, end: \
                        rec[END] >= start and rec[END] <= end
    else:
        sys.exit("Unexpected value for job_type: %s" % (job_type,))

    # Read all records.
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        records.append( (rec.times_start[rec.REAL_TIME],
            rec.times_end[rec.REAL_TIME], rec.tool, rec.pid) )

        ppids[rec.ppid] = None

    # Remove parent-processes from records
    records = [rec for rec in records
                    if not ppids.has_key(rec[PID])]

    # Find end points
    start_time = min( [rec[START] for rec in records] )
    end_time = max( [rec[END] for rec in records] )

    duration = end_time - start_time
    part_duration = duration / numparts

    # Report each partition
    for part in range(numparts):
        part_start = start_time + part * part_duration

        # Ensure we get everything, even after rounding errors
        if part == numparts - 1:
            part_end = end_time
        else:
            part_end = start_time + (part + 1) * part_duration

        print "Partition #%d  From %s to %s (%s - %s of build), duration: %s" % \
                (part + 1, part_start, part_end,
                        LOG.hms(part_start - start_time),
                        LOG.hms(part_end - start_time),
                        LOG.hms(part_duration))

        # Find the records for this partition
        if part == numparts - 1:
            part_recs = [rec for rec in records
                            if job_func_end(rec, part_start, part_end)]
        else:
            part_recs = [rec for rec in records
                            if job_func_any(rec, part_start, part_end)]

        print_summary(part_recs)
        print
        print


def print_summary(recs):
    tools = {}
    for rec in recs:
        if not tools.has_key(rec[TOOL]):
            tools[rec[TOOL]] = 1
        else:
            tools[rec[TOOL]] += 1

    toolnames = tools.keys()
    toolnames.sort()
    for tool in toolnames:
        print "\t%6d %s" % (tools[tool], tool)

    print "\t%6d TOTAL" % (len(recs),)
