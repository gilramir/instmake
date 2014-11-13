# Copyright (c) 2014 by Cisco Systems, Inc.
"""
Conversions related to Electric Cloud's Electric Accelerator (emake).
The is useful for reading instmake data in Electric Insight
"""
from instmakelib import instmake_log as LOG
import sys
from instmakelib import pidtree
import getopt

from xml.sax.saxutils import escape

description = "Create an Electric Accelerator annotation file"

def usage():
    print "einsight:", description

job_id = 0
build_start = None
slots = None

class Timeline:
    def __init__(self):
        self.recs = []
        self.pids = {}

    def hasRec(self, rec):
        return self.pids.has_key(rec.pid)

    def addIfPossible(self, rec):
        """Add a rec if possible. Returns True if added,
        False if not."""

        invoked = rec.times_start[rec.REAL_TIME]
        completed = rec.times_end[rec.REAL_TIME]

        take_it = False

        if self.recs:
            self.busy_start = self.recs[0].times_start[rec.REAL_TIME]
            self.busy_end = self.recs[-1].times_end[rec.REAL_TIME]
        else:
            self.busy_start = None
            self.busy_end = None

        # Are we empty?
        if len(self.recs) == 0:
            take_it = True
            self.recs.append(rec)

        # Does the job precede all our jobs?
        elif completed <= self.busy_start:
            take_it = True
            self.recs.insert(0, rec)

        # Does the job start after all our jobs?
        elif invoked >= self.busy_end:
            take_it = True
            self.recs.append(rec)

        # Let's see if we have a gap where the job will fit
        else:
            # Find the jobs surrounding the job's start time
            prev_rec = None
            for i, rec in enumerate(self.recs):
                # Skip the first rec
                if prev_rec == None:
                    prev_rec = rec
                    continue

                prev_end = prev_rec.times_end[rec.REAL_TIME]
                this_start = rec.times_start[rec.REAL_TIME]

                # Is this job between the previous end time
                # and this start time?
                if invoked >= prev_end and invoked <= this_start:
                    # Make sure they all 3 don't coincide
                    if invoked == prev_end == this_start:
                        break

                    # We found the gab where this job could start
                    # But, does this job end before this other job starts?
                    if completed <= this_start:
                        self.recs.insert(i, rec)
                        take_it = True
                        break
        if take_it:
            self.pids[rec.pid] = None

        return take_it

class Slots:
    def __init__(self):
        self.timelines = []

    def addRecord(self, rec):
        for j, timeline in enumerate(self.timelines):
            if timeline.addIfPossible(rec) == True:
                return j
        else:
            # No timeline could hold this. We need a new timelin!
            timeline = Timeline()
            assert timeline.addIfPossible(rec) == True
            self.timelines.append(timeline)
            return len(self.timelines) - 1

    def slotThatHoldsRec(self, rec):
        # Return the number of the slot where a PID is found
        for j, timeline in enumerate(self.timelines):
            if timeline.hasRec(rec):
                return j

        return None


def print_srec(srec, make_level):
    rec = srec.Rec()

    children_srecs = srec.Children()

    if children_srecs:
        # We are a Make process.
        is_make_process = True
        print anno_make_start(make_level, rec)
        make_level += 1
    else:
        is_make_process = False

    # Print our job record
    if not is_make_process:
        print_job_rec(rec)

    if children_srecs:
        children_srecs.sort()

        for child_srec in children_srecs:
            print_srec(child_srec, make_level)

        print anno_make_end()

def print_job_rec(rec):
    global job_id

    slots.addRecord(rec)

    job_id += 1
    print anno_job(rec, job_id)

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


def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'einsight' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = "m"
    longopts = ["full", "make", "make-targets"]

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

    global slots
    slots = Slots()

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

    print anno_header()

    srec = ptree.TopSRec()
    if not srec:
        sys.exit("Unable to find top-most record.")

    # Get some initial data
    global build_start
    rec = srec.Rec()
    build_start = rec.times_start[rec.REAL_TIME]

    print_srec(srec, 0)

    print anno_footer()


def anno_header():
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE build SYSTEM "build.dtd">
<build id="15903" localAgents="true" cm="sjc-buildcm1b:8030" start="Fri Aug 29 2 3:48:00 2014">
<properties></properties>
<environment></environment>
"""

def anno_footer():
    return """</build>"""

def anno_make_start(make_level, rec):
    # XXX
    escaped_cmdline = escape(rec.cmdline).replace('"', 'Q') 
    return """<make level="%d" cmd="%s" cwd="%s">""" % \
            (make_level, escaped_cmdline, rec.cwd)

def anno_make_end():
    return "</make>"

def anno_job(rec, job_id):
    job_id_string = "J%016x" % (job_id,)

    invoked = rec.times_start[rec.REAL_TIME] - build_start
    completed = rec.times_end[rec.REAL_TIME] - build_start

    escaped_cmdline = escape(rec.cmdline)

    slot = slots.slotThatHoldsRec(rec)
    if slot == None:
        # ???
        return

    #return """<job id="%s"  start="10542" end="10543" weight="
    x =  """<job id="%s" type="rule">""" % (job_id_string,)
    x += """<command>
<argv>%s</argv>
<output src="prog">%s
</output>
</command>
<timing invoked="%f" completed="%f" node="localhost-%d"/>
</job>""" % (escaped_cmdline, escaped_cmdline, invoked, completed, slot)

    return x
