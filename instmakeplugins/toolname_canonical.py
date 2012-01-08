# Copyright (c) 2010 by Cisco Systems, Inc.
"""
ToolName plugin to canonicalize tool names that start with "../" or "./"
"""

import re
import os

def first_arg_regex_cb(first_arg, argv, cwd, m):
    if cwd == None:
        return argv
    joined = os.path.join(cwd, first_arg)
    canonical = os.path.normpath(joined)
    return [canonical] + argv[1:]

def register(manager):
    re_relative = re.compile("^\.{1,2}/")
    manager.RegisterFirstArgumentRegex(re_relative, first_arg_regex_cb)
