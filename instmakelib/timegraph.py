# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Timeline graph
"""
import sys
import os
from instmakelib import pidtree
from instmakelib import linearmap

ALL_PROCS = 0
ONLY_MAKES = 1

B_START = linearmap.B_START
B_END = linearmap.B_END

class JobRec:
    """Wrapper around the LogRecord class. Has to keep track
    of any JobPaths that emanate from this record."""

    def __init__(self, rec):
        self.rec = rec
        self.paths = []
        self.tool = os.path.basename(rec.tool)
        if rec.make_target:
            self.target = os.path.basename(rec.make_target)
        else:
            self.target = ""

    def Rec(self):
        return self.rec

    def PPID(self):
        return self.rec.ppid

    def PID(self):
        return self.rec.pid

    def Paths(self):
        return self.paths

    def AddChild(self, child_jrec):
        rec = child_jrec.Rec()
        start_time = rec.times_start[rec.REAL_TIME]

        for path in self.paths:
            if start_time > path.LastEndTime():
                path.Add(child_jrec)
                return
        else:
            path = JobPath()
            path.Add(child_jrec)
            self.paths.append(path)

    def __cmp__(self, other):
        return cmp(self.rec.times_start[self.rec.REAL_TIME],
            other.rec.times_start[other.rec.REAL_TIME])

class JobPath:
    """A serial path of execution which can execute many jobs,
    one at a time. No jobs must overlap."""

    def __init__(self):
        self.jrecs = []
        self.last_end_time = 0

    def JRecs(self):
        return self.jrecs

    def LastEndTime(self):
        return self.last_end_time

    def Add(self, jrec):
        self.jrecs.append(jrec)

        # We know we're processing in sorted time order,
        # so this new end-time will automatically be >= to the
        # saved end-time.
        rec = jrec.Rec()
        self.last_end_time = rec.times_end[rec.REAL_TIME]


class JobTree(pidtree.PIDTree):
    """A JobTree is like a PIDTree except that nodes have multiple
    children arrays correlating to sequential paths of execution."""

    RecClass = JobRec

    def TopJRec(self):
        return self.TopSRec()

    def GetJRec(self, pid):
        return self.GetSRec(pid)

    def JRecs(self):
        return self.SRecs()


class TimeGraph:
    """Keeps track of the JTree and the LinearMap that are necessary
    for creating a time graph."""
    def __init__(self, log, process_types):

        self.jtree = JobTree()
        self.Lmap = linearmap.LinearMap()

        # Get all the recs from the instmake log
        while 1:
            try:
                rec = log.read_record()
            except EOFError:
                log.close()
                break

            self.jtree.AddRec(rec)

        self.jtree.Finish() 

        self.top_jrec = self.jtree.TopJRec()
        if not self.top_jrec:
            sys.exit("Unable to find top-most record.")

        def add_rec(linear_map, rec):
            start = rec.times_start[rec.REAL_TIME]
            length = rec.diff_times[rec.REAL_TIME]
            linear_map.Add(start, length, rec.pid, None)

        # Create the Lmap
        if process_types == ONLY_MAKES:
            for jrec in self.jtree.JRecs():
                if jrec.paths:
                    add_rec(self.Lmap, jrec.Rec())
        else:
            for rec in self.jtree.Recs():
                add_rec(self.Lmap, rec)

    def TopJRec(self):
        return self.top_jrec

    def JRecItems(self):
        return self.jtree.pids.items()

    def BoundaryArrays(self):
        return self.Lmap.BoundaryArrays()

    def GetJRec(self, pid):
        return self.jtree.GetJRec(pid)

