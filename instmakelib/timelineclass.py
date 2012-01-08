# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Maintains a timeline of record PIDs.
"""

class Timeline:
    START = 0
    FINISH = 1

    def __init__(self):
        self.start_time = -1
        self.finish_time = -1
        self.min_nonzero_time = -1

        self.total_time = 0
        self.num_recs = 0

        # Key = time, Value = [ (START|FINISH, PID) ]
        self.transitions = {}

        # Filled-in after Finalize()
        # Contains all the transition times, in order
        self.transition_times = []

        # Filled-in after Finalize()
        # Contains each transition-delimited chunk of time.
        # Items are tuples: (start_time, finish_time, [PIDs])
        self.chunks = []

    def NumRecords(self):
        return self.num_recs

    def StartTime(self):
        return self.start_time

    def FinishTime(self):
        return self.finish_time

    def TotalTime(self):
        return self.total_time

    def Record(self, rec):
        """Record the start and finish"""
        start_tuple = (self.START, rec.pid)
        start_time = rec.times_start[rec.REAL_TIME]
        transitions = self.transitions.setdefault(start_time, [])
        transitions.append(start_tuple)

        finish_tuple = (self.FINISH, rec.pid)
        finish_time = rec.times_end[rec.REAL_TIME]
        transitions = self.transitions.setdefault(finish_time, [])
        transitions.append(finish_tuple)

        if self.start_time == -1:
            self.start_time = start_time
        else:
            self.start_time = min(self.start_time, start_time)

        self.finish_time = max(self.finish_time, finish_time)
        
        duration = finish_time - start_time
        self.total_time += duration
        self.num_recs += 1

        if duration > 0:
            if self.min_nonzero_time == -1:
                self.min_nonzero_time = duration
            else:
                self.min_nonzero_time = min(self.min_nonzero_time, duration)


    def Finalize(self):
        self.transition_times = self.transitions.keys()
        self.transition_times.sort()
        
        self.chunks = []
        last_time = -1
        current_pids = []
        time = -1

        for time in self.transition_times:
            transition_tuples = self.transitions[time]
#            print time, current_pids, transition_tuples
            start_pids = [t[1] for t in transition_tuples
                    if t[0] == self.START]
            finish_pids = [t[1] for t in transition_tuples
                    if t[0] == self.FINISH]

            if last_time == -1:
                assert start_pids
                assert not finish_pids

                current_pids.extend(start_pids)
                last_time = time
                continue

            else:
                if finish_pids:
                    zero_time_pids = [p for p in finish_pids if
                            p in start_pids]
                    if zero_time_pids: # 061040.17841
                        current_pids.extend(zero_time_pids)
                        for pid in zero_time_pids:
                            start_pids.remove(pid)

                    chunk = (last_time, time, current_pids[:])
                    self.chunks.append(chunk)
                    for pid in finish_pids:
                        current_pids.remove(pid)

                if start_pids:

                    # Was there a chunk with no pids?
                    if not finish_pids and not current_pids:
                        empty_chunk = (last_time, time, [])
                        self.chunks.append(empty_chunk)
                    current_pids.extend(start_pids)

                last_time = time

        return

    def MeanRecs(self, num_parts):

        T_START = 0
        T_FINISH = 1

        time_interval = (self.finish_time - self.start_time) / num_parts
        time_boundaries = []
        current_time = self.start_time
        for i in range(num_parts):
            next_time = current_time + time_interval
            # The last chunk will have a little bit of extra time
            # so that "< finish" will evaluate as true:
            if i == num_parts - 1:
                time_boundaries.append( (current_time, next_time + 0.01) )
            else:
                time_boundaries.append( (current_time, next_time) )
            current_time = next_time

        C_START = 0
        C_FINISH = 1
        C_PID = 2

        # List of lists; each item-list is a list of PIDs
        grouped_chunks = []
        for times in time_boundaries:
            (start, finish) = times
            chunks = [c for c in self.chunks if \
                    (c[C_START] >= start and c[C_START] < finish) or \
                    (c[C_FINISH] >= start and c[C_FINISH] < finish) or \
                    (c[C_START] <= start and c[C_FINISH] >= finish)]
            grouped_chunks.append(chunks)

        self.means = []


        for i, chunks in enumerate(grouped_chunks):
            total_ticks = 0.0
            total_weighted_n = 0.0

            group_start, group_finish = time_boundaries[i]

            for chunk in chunks:
                (chunk_start, chunk_finish, pids) = chunk

                floor_start = max(group_start, chunk_start)
                ceiling_finish = min(group_finish, chunk_finish)

                ticks = (ceiling_finish - floor_start) / self.min_nonzero_time

                total_ticks += ticks
                total_weighted_n += ticks * len(pids)

            if total_ticks == 0.0:
                mean = 0.0
            else:
                mean = total_weighted_n / total_ticks
            means_record = (time_boundaries[i][T_START],
                    time_boundaries[i][T_FINISH], mean)
            self.means.append(means_record)

        return self.means
