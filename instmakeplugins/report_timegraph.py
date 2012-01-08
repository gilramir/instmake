# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Timeline graph
"""
import sys
import getopt
from instmakelib import pidtree
from instmakelib import timegraph
from instmakelib import instmake_log as LOG
import os

description = "Create an ASCII-art graph of process timeline."

def usage():
    print "timegraph: [OPTS]", description
    print "\t-m : Report only 'make' processes."


def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'timegraph' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = "m"
    longopts = []
    process_types = timegraph.ALL_PROCS

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-m":
            process_types = timegraph.ONLY_MAKES
        else:
            sys.ext("Unexpected option %s" % (opt,))

    run_timeline(log_file_name, process_types)

JREC_X_SEP = 2
JREC_Y_HEIGHT = 7

LINE_DASHES = 0
LINE_PID = 1
LINE_TOOL = 2
LINE_TARGET = 3
LINE_VLINE = 4
LINE_BRANCHES = 5
LINE_BRANCH_VLINES = 6

class JobRecView:
    """View class that correspondes to the JobRec class."""
    def __init__(self, jrec, pid_hash):
        pid_hash[jrec.rec.pid] = self
        self.jrec = jrec
        self.path_views = []

        for path in jrec.paths:
            self.path_views.append(JobPathView(path, pid_hash))

        self.center_offset = None
        self.text_width = max(len(jrec.rec.pid), len(jrec.tool), len(jrec.target))
        self.logical_width = None
        self.children_width = None

    def JRec(self):
        return self.jrec

    def PrintStart(self, lines):
        lines[LINE_DASHES].PrintCenteredAt(self.center_offset,
            "=" * self.text_width)

        lines[LINE_PID].PrintCenteredAt(self.center_offset, self.jrec.rec.pid)
        lines[LINE_TOOL].PrintCenteredAt(self.center_offset, self.jrec.tool)

        if self.jrec.target:
            lines[LINE_TARGET].PrintCenteredAt(self.center_offset,
                self.jrec.target)

        # Children?
        if self.path_views:
            lines[LINE_VLINE].PrintAt(self.center_offset, "|")

        # More than one child?
        if len(self.path_views) > 1:
            first_child_center = self.path_views[0].center_offset
            last_child_center = self.path_views[-1].center_offset
            lines[LINE_BRANCHES].PrintAt(first_child_center,
                "-" * (last_child_center - first_child_center))

            # Place "+"'s at each child
            for path_view in self.path_views:
                lines[LINE_BRANCHES].PrintAt(path_view.center_offset, "+")

            # Place "|"'s at each child
            for path_view in self.path_views:
                lines[LINE_BRANCH_VLINES].PrintAt(path_view.center_offset, "|")

        # How much should print routine scroll?
        if len(self.path_views) == 0:
            if self.jrec.target:
                return LINE_TARGET + 1
            else:
                return LINE_TOOL + 1
        elif len(self.path_views) == 1:
            return LINE_VLINE + 1
        else:
            return LINE_BRANCH_VLINES + 1

    def PrintStartAndEnd(self, lines):
        assert len(self.path_views) == 0, "Too many paths for Start/End PID=%s" \
            % (self.jrec.rec.pid,)

        line_num = self.PrintStart(lines)

        end = "^=" * (self.text_width / 2 + 1)

        lines[line_num].PrintCenteredAt(self.center_offset,
                end[:self.text_width])

        return line_num + 1

    def PrintEnd(self, lines):
        lines[LINE_DASHES].PrintCenteredAt(self.center_offset,
            "^" * self.text_width)

    def PrintContinuation(self, lines, num_to_scroll):
        if not self.path_views:
            for i in range(num_to_scroll):
                lines[i].PrintAt(self.center_offset, ".")

    def SetCenterOffset(self, center_offset):
        self.center_offset = center_offset

        x_offset = self.center_offset - (self.children_width / 2)

        for path in self.path_views:
            path.SetXOffset(x_offset)
            x_offset += path.LogicalWidth() + JREC_X_SEP

    def CalculateWidth(self):
        self.children_width = 0

        for path_view in self.path_views:
            if self.children_width > 0:
                self.children_width += JREC_X_SEP

            self.children_width += path_view.CalculateWidth()

        self.logical_width = max(self.children_width, self.text_width)

        return self.logical_width

    def __cmp__(self, other):
        return cmp(self.jrec, other.jrec)

class JobPathView:
    """View class which corresponds to a JobPath."""

    def __init__(self, jpath, pid_hash):
        self.jpath = jpath
        self.jrec_views = []

        for jrec in jpath.JRecs():
            self.jrec_views.append(JobRecView(jrec, pid_hash))

        self.logical_width = None
        self.center_offset = None

    def Path(self):
        return self.path

    def LogicalWidth(self):
        return self.logical_width

    def CalculateWidth(self):
        self.logical_width = 0

        if self.jrec_views:
            jrec_widths = map(JobRecView.CalculateWidth, self.jrec_views)
            self.logical_width = max(jrec_widths)

        return self.logical_width

    def SetXOffset(self, x_offset):
        self.center_offset = x_offset + (self.logical_width / 2)

        for jrec_view in self.jrec_views:
            jrec_view.SetCenterOffset(self.center_offset)


class FormattedLine:
    """A buffer to hold a line of text. It's easy to print to any place
    in the line and have it automatically adjust its size appropriately."""

    def __init__(self, width=None):
        if not width:
            self.line = ""
        else:
            self.line = " " * width


    def PrintAt(self, pos, text):
#        print "WAS:", self.line, "<<<"
        if len(self.line) < pos:
            self.line += " " * (pos - len(self.line))

        uses = pos + len(text)
        self.line = self.line[:pos] + text + self.line[uses:]
#        print "NOW:", self.line, "<<<"


    def PrintCenteredAt(self, pos, text):
        start = pos - (len(text)/2)
        self.PrintAt(start, text)

    def Line(self):
        return self.line



def run_timeline(log_file_name, process_types):

    # Open the log file
    log = LOG.LogFile(log_file_name)

    graph_model = timegraph.TimeGraph(log, process_types)

    # Create JobRecView and JobPathView objects
    jrecview_pids = {}
    top_jrec = graph_model.TopJRec()
    top_jrec_view = JobRecView(top_jrec, jrecview_pids)

    # Run the report
    tree_width = top_jrec_view.CalculateWidth()
    top_jrec_view.SetCenterOffset(tree_width / 2)

    # Maintain an array of FormattedLines long enough
    # to print a single JobRec.
    lines = []
    for i in range(JREC_Y_HEIGHT):
        lines.append(FormattedLine(tree_width))

    pid_started = {}

    boundary_arrays = graph_model.BoundaryArrays()

    for boundary_array in boundary_arrays:
        num_to_scroll = 1


        # Sometimes a record will magically start and end at the
        # same time. Blame faulty timestamps for that. But we have
        # to have a mechanism to handle that. So we keep track of which
        # of the boundaries are for the ends of processes.
        ends = filter(lambda x: x.Type() == timegraph.B_END, boundary_array)
        end_pids = map(lambda x: x.Name(), ends)

        ignore_cont = {}
        ignore_end = {}

        for boundary in boundary_array:
            pid = boundary.Name()
            boundary_type = boundary.Type()
            jrec_view = jrecview_pids[pid]

            if boundary_type == timegraph.B_START:
                # Does this set of boundaries include a starting boundary
                # and end boundary for the same record?
                if pid in end_pids:
                    scroll = jrec_view.PrintStartAndEnd(lines)
                    ignore_end[pid] = None
                else:
                    scroll = jrec_view.PrintStart(lines)
                    pid_started[pid] = None
                    ignore_cont[pid] = None

                num_to_scroll = max(num_to_scroll, scroll)

            elif boundary_type == timegraph.B_END:
                if not ignore_end.has_key(pid):
                    jrec_view.PrintEnd(lines)
                    del pid_started[pid]
            else:
                sys.exit("Unhandled boundary type: %s" % (boundary_type,))

        # Print pretty dots to show the inside of a record.
        for pid in pid_started.keys():
            if not ignore_cont.has_key(pid):
                jrec_view = jrecview_pids[pid]
                jrec_view.PrintContinuation(lines, num_to_scroll)

        # Print the first FormattedLine and shift array.
        for i in range(num_to_scroll):
            print lines[0].Line()
            del lines[0]
            lines.append(FormattedLine(tree_width))

    # Print the remaining FormattedLines
    for line in lines:
        print line.Line()

