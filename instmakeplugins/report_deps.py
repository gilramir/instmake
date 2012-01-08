# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Report dependencies.
"""

from instmakelib import instmake_log as LOG
import sys
from instmakelib import graph

description = "Show file/action dependencies for instmake logs with clearaudit info."

def usage():
    print "deps:", description


def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'deps' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Open the log file
    log = LOG.LogFile(log_file_name)

    dag = graph.DAG()

    # Read the log records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        action_name = "PID " + rec.pid + " " + rec.tool
        dag.AddNode(action_name)

        # input_files may be None, so check
        if rec.input_files:
            for input_file in rec.input_files:
                filename = LOG.nxname(input_file)
                dag.AddNode(filename)
                dag.AddEdge(filename, action_name)

        # output_files may be None, so check
        if rec.output_files:
            for output_file in rec.output_files:
                filename = LOG.nxname(output_file)
                dag.AddNode(filename)
                dag.AddEdge(action_name, filename)

    dag.Write(sys.stdout)
