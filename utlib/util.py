# Copyright (c) 2012 by Cisco Systems, Inc.

import subprocess

SUCCESS = 0
def exec_cmdv(cmdv):
    """Execute a list of arguments, and return (retval, output),
    where output is stdout and stderr combined"""
    try:
        output = subprocess.check_output(cmdv, stderr=subprocess.STDOUT)
        retval = SUCCESS

    except OSError, e:
        output = str(e)
        retval = None

    except subprocess.CalledProcessError, e:
        output = e.output
        retval = e.returncode

    return (retval, output)
