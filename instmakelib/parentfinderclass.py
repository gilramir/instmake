# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Keeps track of Record PIDs so we can determine
if a rec has children, and is thus a Make process.
"""

class ParentFinder:
    """This class takes advantage of the fact that the instmake
    log is written after a process finishes. So all parent processes
    will be written to the log after their children processes. When
    we read a child record we can note the parent PID. Later, when its
    time to check the parent rec, its PID will have been noted, so we
    know that it is a parent record."""
    def __init__(self):
        self.parent_pids = {}

    def Record(self, rec):
        self.parent_pids[rec.ppid] = None

    def IsParent(self, rec):
        if self.parent_pids.has_key(rec.pid):
            return 1
        else:
            return 0
