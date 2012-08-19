# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Keep track of concurrent processes.
"""

import sys
from instmakelib import instmake_log as LOG
from instmakelib import pidtree
from instmakelib import linearmap

false = 0
true = not false

ALL = 0
NON_MAKE = 1
ONLY_MAKE = 2
SPECIFIC_PIDS = 3

class Concurrency:
    def __init__(self, log_file_name, proc_mode, save_args=0,
        save_tools=0, **kwargs):

        only_pids = None
        require_top_rec = 1
        keep_recs = None

        self.recs_by_pid = {}

        if kwargs.has_key("require_top_rec"):
            require_top_rec = kwargs["require_top_rec"]

        if kwargs.has_key("only_pids"):
            only_pids = kwargs["only_pids"]

        if kwargs.has_key("keep_recs"):
            keep_recs = kwargs["keep_recs"]

        # Open the log file
        log = LOG.LogFile(log_file_name)

        # The linear map will keep track of concurrency for us.
        # In our case, the map is mapping time. At each time
        # interval, various jobs may be running.
        map = linearmap.LinearMap()

        # Keep the map class from doing things it normally does,
        # if the user ends up requesting the LinearMap object
        # to print a map to stdout.
        map.PrintRawOffsets()
        map.NoPrintDiff()
        self.map = map

        # The "top" record... the record with no parent.
        self.top_rec = None
        ptree = None

        # If we care about which jobs are either 'make' or not
        # 'make', then we need a PID tree, because it is the
        # branches in the PID tree that are the 'make' jobs.
        if proc_mode == NON_MAKE or proc_mode == ONLY_MAKE:
            ptree = pidtree.PIDTreeLight()

        # Saves the tool for the LinearMap Item ID.
        if save_tools:
            self.tool_for_id = {}

        # Read all the records and create the map
        while 1:
            try:
                rec = log.read_record()
            except EOFError:
                log.close()
                break

            # If looking only for certain PIDs, is this one of them?
            if proc_mode == SPECIFIC_PIDS:
                if not rec.pid in only_pids:
                    continue

            start = rec.times_start[rec.REAL_TIME]
            length = rec.diff_times[rec.REAL_TIME]

            if save_args:
                ID = map.Add(start, length, rec.pid, rec.cmdline)
            else:
                ID = map.Add(start, length, rec.pid, None)

            if save_tools:
                self.tool_for_id[ID] = rec.tool

            # Keep the rec data?
            if keep_recs:
                if self.recs_by_pid.has_key(rec.pid):
                    sys.exit("Two records have PID %s" % (rec.pid,))
                self.recs_by_pid[rec.pid] = rec

            # If we're construting a PID-tree, then add this
            # record to it.
            if ptree:
                ptree.AddRec(rec)

            if rec.ppid == None:
                if self.top_rec:
                    print "Found another record with no PPID."
                self.top_rec = rec

        if require_top_rec and not self.top_rec:
            sys.exit("No top-most record found in %s" % (log_file_name,))

        # Retrieve the data from the map
        jobslot_duration = []
        tot_time = 0.0
        self.jobslot_ids = []

        if ptree:
            # Either NON_MAKE or ONLY_MAKE, so count only
            # some of the jobs. To do so, we have to figure out
            # which IDs correspond to makes.
            make_pids = ptree.BranchPIDs()

            # Look at each time slice in the map
            for chunk in map.Chunks():
                item_ids = []

                # Remove the jobs we're not interested in.
                for id in chunk.IDs():
                    pid = map.ItemName(id)
                    if proc_mode == NON_MAKE:
                        # Only count the non-make jobs
                        if not pid in make_pids:
                            item_ids.append(id)
                    elif proc_mode == ONLY_MAKE:
                        # Only count the make jobs
                        if pid in make_pids:
                            item_ids.append(id)
                    else:
                        assert 0

                # Now do the counting
                jobslot = len(item_ids)

                # Add the chunk length (real time)
                # to the time allocated to this jobslot.
                while len(jobslot_duration) <= jobslot:
                    jobslot_duration.append(0)

                jobslot_duration[jobslot] += chunk.Length()
                tot_time += chunk.Length()

                # Add the IDs that were running in this
                # time interval. We can repeat IDs because the
                # same job will be running at various time
                # slots. Thus, Use a hash.
                while len(self.jobslot_ids) <= jobslot:
                    self.jobslot_ids.append({})

                for ID in item_ids:
                    self.jobslot_ids[jobslot][ID] = None


        else:
            # Count all jobs
            for chunk in map.Chunks():
                item_ids = chunk.IDs()
                jobslot = len(item_ids)

                # Add the chunk length (real time)
                # to the time allocated to this jobslot.
                while len(jobslot_duration) <= jobslot:
                    jobslot_duration.append(0)

                jobslot_duration[jobslot] += chunk.Length()
                tot_time += chunk.Length()

                # Add the IDs that were running in this
                # time interval. We can repeat IDs because the
                # same job will be running at various time
                # slots. Thus, Use a hash.
                while len(self.jobslot_ids) <= jobslot:
                    self.jobslot_ids.append({})

                for ID in item_ids:
                    self.jobslot_ids[jobslot][ID] = None

        # When reporting makes (ALL, or ONLY_MAKE),
        # we don't need to start counting at jobslot 0,
        # because we always have at least 1 job (the initial make).
        # But when reporting non-makes, we do have to start
        # counting at jobslot 0, because make can be running
        # w/o spawning any jobs.
        if proc_mode == NON_MAKE:
            jobslot_start = 0
        else:
            jobslot_start = 1

        self.results = []
        self.series_data = []
        self.series_numjobs = []

        # Calculate percentages
        jobslot = jobslot_start
        for duration in jobslot_duration[jobslot_start:]:
            pct_duration = duration * 100 / tot_time

            self.results.append((jobslot, pct_duration))
            self.series_data.append(pct_duration)
            self.series_numjobs.append(jobslot)

            jobslot += 1

    def Results(self):
        return self.results

    def SeriesData(self):
        return self.series_data

    def SeriesNumJobs(self):
        return self.series_numjobs

    def TopRecord(self):
        return self.top_rec

    def Map(self):
        return self.map
 
    def NumJobSlots(self):
        return len(self.jobslot_ids)

    def PrintMap(self, fh):
        self.map.PrintMap(fh)

    def IDsForJ(self, j):
        return self.jobslot_ids[j].keys()

    def ToolsForJ(self, j):
        IDs = self.jobslot_ids[j].keys()
        tools = []
        for ID in IDs:
            tools.append(self.tool_for_id[ID])

        return tools

    def PIDsForJ(self, j):
        IDs = self.jobslot_ids[j].keys()

        pids = {}
        for ID in IDs:
            pids[self.map.ItemName(ID)] = None

        return pids.keys()

    def Rec(self, pid):
        return self.recs_by_pid[pid]
