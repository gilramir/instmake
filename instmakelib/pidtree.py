# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Create a PID-tree from the log records.

The PIDTree is a heavy-weight class because it keeps track
of SortableRec's, which are wrappers around instmake-log records objects.
Thus, a lot of memory is used because the instmake-log records are
kept in memory.

The PIDTreeLight is a light-weight class because it keeps track
of PIDs only. It does not keep the instmake-log record in memory.
"""

import sys

class SortableRec:
    """A wrapper around an instmakelog record object. The SortableRec knows
    about its children records, and as the name suggests, the SortableRec
    can be sorted in an array."""

    def __init__(self, rec):
        self.rec = rec
        self.children = []

    def Children(self):
        """Returns the list of children SortableRec's for this object."""
        return self.children

    def Rec(self):
        """Return the instmake_log.Record that is wrapped by this object."""
        return self.rec

    def AddChild(self, child_srec):
        self.children.append(child_srec)

    MAKE_TAG = "make-internal-function"
    len_MAKE_TAG = len(MAKE_TAG)

    def PrintTree(self, indent=0):
        spaces = "  " * indent
        if self.rec.cmdline[:self.len_MAKE_TAG] == self.MAKE_TAG:
            tool = self.rec.cmdline[self.len_MAKE_TAG+1:]
        else:
            tool = self.rec.tool

        print "%sPID=%s %s" % (spaces, self.rec.pid, tool),

        if self.rec.make_target:
            print "  TARGET=%s" % (self.rec.make_target,)
        else:
            print

        if self.children:
            print "%sCWD=%s" % (spaces, self.rec.cwd)
            print "%sCMDLINE=%s" % (spaces, self.rec.cmdline)
            print

        # Recurse
        indent += 1
        self.children.sort()
        for child_srec in self.children:
            child_srec.PrintTree(indent)

    def Walk(self, cb, user_data=None, indent=0):
        cb(self.rec, user_data, indent)

        # Recurse
        indent += 1
        self.children.sort()
        for child_srec in self.children:
            child_srec.Walk(cb, user_data, indent)

    def WalkBackwards(self, cb, user_data=None, indent=0):
        cb(self.rec, user_data, indent)

        # Recurse
        indent += 1
        self.children.sort()
        rchildren = self.children[:]
        rchildren.reverse()
        for child_srec in rchildren:
            child_srec.WalkBackwards(cb, user_data, indent)

    def PID(self):
        return self.rec.pid

    def PPID(self):
        return self.rec.ppid

    def __cmp__(self, other):
        return cmp(self.rec.times_start[self.rec.REAL_TIME],
            other.rec.times_start[other.rec.REAL_TIME])

    def __repr__(self):
        return "<pidtree.SRec PID=%s>" % (self.rec.pid,)


class PIDTree:

    RecClass = SortableRec   

    """A PID tree, using PID and PPID from an instmake_log.Record."""
    def __init__(self):
        self.top_srec = None
        self.pids = {}

    def NumSRecs(self):
        return len(self.pids.values())

    def SubPIDTree(self, pid):
        """Return a new PIDTree with the pid SRec as the root node."""
        new_ptree = PIDTree()
        new_ptree.top_srec = self.pids[pid]
        self._SubPIDTreeHelper(new_ptree, pid)
        return new_ptree

    def _SubPIDTreeHelper(self, new_ptree, pid):
        srec = self.pids[pid]
        new_ptree.pids[pid] = srec
        for child_srec in srec.Children():
            self._SubPIDTreeHelper(new_ptree, child_srec.Rec().pid)


    def AddRec(self, rec):
        """Add a record to the PIDTree."""
        srec = self.RecClass(rec)
        if self.pids.has_key(rec.pid):
            print >> sys.stderr, "Warning: detected multiple PID=%s" % \
                (rec.pid,)

        self.pids[rec.pid] = srec

    def GetSRec(self, pid):
        """Given a PID, returns the SortableRec for that PID. Raises
        KeyError if the PID is not in the tree."""
        return self.pids[pid]

    def SRecs(self):
        """Return the list of SortableRec's in the PIDTree."""
        return self.pids.values()

    def TopSRec(self):
        """Returns the top-most SortableRec."""
        return self.top_srec

    def TopRec(self):
        """Returnst he top-most instmake_log.Record."""
        if self.top_srec:
            return self.top_srec.Rec()
        else:
            return None

    def Finish(self):
        """The user needs to call this after all records are added to
        the PIDTree; this function ties the records together via their
        PIDs and PPIDs."""
        # Now that we have all the PIDS, tie them to their PPIDs.
        srecs = self.pids.values()
        srecs.sort()

        for srec in srecs:
            ppid = srec.PPID()
            if ppid == None:
                if self.top_srec != None:
                    print >> sys.stderr, "Warning: detected multiple root records."
                else:
                    self.top_srec = srec
            else:
                if not self.pids.has_key(ppid):
                    print >> sys.stderr, "Warning: couldn't find PID=%s" % (ppid,)
                    continue
                parent_srec = self.pids[ppid]
                parent_srec.AddChild(srec)

    def Print(self):
        """Print the tree."""
        if self.top_srec:
            self.top_srec.PrintTree()
        else:
            print "Top record not found."

    def Walk(self, cb, user_data=None):
        """Walk the tree, calling a callback function for each record."""
        if self.top_srec:
            self.top_srec.Walk(cb, user_data)
        else:
            print "Top record not found."

    def WalkBackwards(self, cb, user_data=None):
        """Walk the tree, calling a callback function for each record."""
        if self.top_srec:
            self.top_srec.WalkBackwards(cb, user_data)
        else:
            print "Top record not found."

    def Recs(self):
        return map(lambda x: x.Rec(), self.SRecs())
        def Append(rec, recs, junk):
            recs.append(rec)

        recs = []
        self.Walk(Append, recs)
        return recs

    def BranchSRecs(self):
        return filter(lambda x: x.Children(), self.SRecs())

class PIDTreeLight:
    """Like PIDTree, but only maintins the PID, not the rec. Uses less
    memory."""
    def __init__(self):
        self.top_pid = None
        # Key = PPID, Value = [PIDs]
        self.child_pids = {}

    def AddRec(self, rec):
        """Add a record to the PIDTree."""
        if rec.ppid == None:
            if self.top_pid != None:
                print "Found another PID w/o PPID."
            self.top_pid = rec.pid
        else:
            children = self.child_pids.setdefault(rec.ppid, [])
            children.append(rec.pid)

    def BranchPIDs(self):
	"""Returns an array the PIDs in the tree that are branches, i.e.,
	the PIDs that have children."""
        return self.child_pids.keys()

    def ChildrenPIDs(self, parent_pid):
	"""Given a PID, returns a list of the children PIDs of that PID.
	The list may be empty, of course. Returns KeyError if the PID that
	the user passes in is not in the tree."""
	return self.child_pids[parent_pid]

    def PIDs(self):
        """Return the list of PIDs in the PIDTreeLight."""
        pids = {}
        pids[self.top_pid] = None

        for pid_list in self.child_pids.values():
            for pid in pid_list:
                pids[pid] = None

        return pids.values()

    def TopPID(self):
        """Returns the top-most PID."""
        return self.top_pid

    def Print(self):
        """Print the tree."""
        if self.top_pid:
            self._PrintTree(self.top_pid)
        else:
            print "Top PID not found."

    def _PrintTree(self, pid, indent=0):
        spaces = "  " * indent
        print "%sPID=%s" % (spaces, pid)

        if self.child_pids.has_key(pid):
            # Recurse
            indent += 1
            children = self.child_pids[pid]
            for child_pid in children:
                self._PrintTree(child_pid, indent)
