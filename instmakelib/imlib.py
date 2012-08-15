# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Common routines for instmake, instmake-graph, and any
other instmake-related programs.
"""

import re
import os
from instmakelib import pluginmanager
from instmakelib import instmake_log

DEFAULT_LOG_FILE = "~/.instmake-log"

# Global config dictionary (set to None before it is initialized)
config = None

def start_plugin_manager(plugin_dirs, plugin_prefixes):

    # Constants
    USER_PLUGIN_DIR = "~/.instmake-plugins"
    PLUGIN_PACKAGE_DIR = "instmakeplugins"
    PLUGIN_PATH_ENV_VAR = "INSTMAKE_PATH"

    pkg_dirs = [ PLUGIN_PACKAGE_DIR ]
    env_vars = [ PLUGIN_PATH_ENV_VAR ]

    fs_dirs = [os.path.expanduser(USER_PLUGIN_DIR)]
    fs_dirs.extend(plugin_dirs)

    prefixes = []
    prefixes.extend(instmake_log.PLUGIN_PREFIXES)
    prefixes.extend(plugin_prefixes)

    return pluginmanager.PluginManager(pkg_dirs, fs_dirs, 
                env_vars, prefixes)


def SetConfig(new_config):
    global config
    config = new_config


def cmp_real_time_start(a, b):
    """cmp() function for comparing real start-time of LogRecords."""
    return cmp(a.times_start[a.REAL_TIME], b.times_start[b.REAL_TIME])


def record_overlaps_records_in_time(rec, records):
    """Check if a single record overlaps any record in a list of LogRecords (in time).
    If there is no overlap, 0 is returned.  If any overlap, 1 is returned."""
    for record in records:
        # 1. Is this rec's start time between
        # the start and end times of another record?
        if rec.times_start[rec.REAL_TIME] >= record.times_start[record.REAL_TIME] \
            and rec.times_start[rec.REAL_TIME] <= record.times_end[record.REAL_TIME]:
            return 1

        # 2. Is this rec's end time between
        # the start and end times of another record?
        if rec.times_end[rec.REAL_TIME] >= record.times_start[record.REAL_TIME] \
            and rec.times_end[rec.REAL_TIME] <= record.times_end[record.REAL_TIME]:
            return 1

        # 3. Does this rec envelope (or coincide exactly with) another record?
        if rec.times_start[rec.REAL_TIME] <= record.times_start[record.REAL_TIME] \
            and rec.times_end[rec.REAL_TIME] >= record.times_end[record.REAL_TIME]:
            return 1
    else:
        # The record doesn't overlap any other record.
        return 0
           

def records_overlap_in_time(records):
    """Check a list of LogRecords to see if any overlap in time.
    If none overlap, 0 is returned. If any overlap, 1 is returned."""

    if len(records) <= 1:
        return 0

    non_overlapping_recs = [records[0]]

    for rec in records[1:]:
        if record_overlaps_records_in_time(rec, non_overlapping_recs):
            return 1
        else:
            # The record doesn't overlap any other record that
            # has been seen. So add it to the "seen" list.
            non_overlapping_recs.append(rec)

    return 0

