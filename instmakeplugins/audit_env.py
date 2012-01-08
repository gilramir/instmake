# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Record all environment variables.
"""

import os
import sys

description = "Record all environment variables"

def usage():
    print "env:", description


def CheckCLI(options):
    if options:
        sys.exit("env plugin has no options")

    return ""


class Auditor:
    def __init__(self, audit_options):
        pass

    def ExecArgs(self, cmdline, instmake_pid):
        return None

    def CommandFinished(self, cexit, cretval):
        return cretval, os.environ

def ParseData(audit_data, log_record):
    """Read the strace data."""
    if audit_data:
        for env_var, env_value in audit_data.items():
            log_record.env_vars[env_var] = env_value
