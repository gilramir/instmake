# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Keep track of simple statistics.
"""

# Ways to sort
SORT_BY_NAME = 0
SORT_BY_TOTAL = 1
SORT_BY_MEAN = 2
SORT_BY_N = 3
SORT_BY_MIN = 4
SORT_BY_MAX = 5
SORT_BY_PCT = 6


class Stat:
    """Keeps track of stats for one item."""

    # Note that this is a class variable so that
    # we can never get into the situation where we're sorting
    # a list of Stat() object, each of which have different
    # 'sort_by' values.
    sort_by = SORT_BY_MEAN

    def __init__(self, name):
        self.name = name
        self.n = 0
        self.total = 0
        self.min = -1
        self.max = -1
        self.mean = -1
        self.pct = -1

    def Add(self, value):
        """Add an observation to the stat object."""
        if self.n == 0:
            self.min = value
            self.max = value
        else:
            self.min = min(self.min, value)
            self.max = max(self.max, value)

        self.n += 1
        self.total +=  value

    def Calculate(self, grand_total):
        """This finishes up the stat object by calculating
        some final numbers. This is more efficient than re-computing
        these numbers every time Add() is called."""
        if self.n != 0:
            self.mean = self.total / float(self.n)
        if grand_total != 0:
            self.pct = 100 * self.total / float(grand_total)

    def Total(self):
        return self.total

    def __cmp__(self, other):
        """Stat objects can be stored in lists, and then the list
        can be sorted normally. The stat object knows on which field to
        sort by using its 'sort_by' field."""
        if self.sort_by == SORT_BY_NAME:
            return cmp(self.name, other.name)
        elif self.sort_by == SORT_BY_TOTAL:
            return cmp(self.total, other.total)
        elif self.sort_by == SORT_BY_MEAN:
            return cmp(self.mean, other.mean)
        elif self.sort_by == SORT_BY_N:
            return cmp(self.n, other.n)
        elif self.sort_by == SORT_BY_MIN:
            return cmp(self.min, other.min)
        elif self.sort_by == SORT_BY_MAX:
            return cmp(self.max, other.max)
        elif self.sort_by == SORT_BY_PCT:
            return cmp(self.pct, other.pct)
        else:
            assert 0

