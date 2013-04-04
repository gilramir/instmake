"""
ToolName plugin to return the name of the perl script.
"""


def basename_match_cb(basename, first_arg, argv, cwd):

    i = 1

    for arg in argv[1:]:

        if len(arg) > 7 and arg[:7] == "--mode=":
            i += 1
            continue

        else:
            return argv[i:]




def register(manager):
    manager.RegisterFirstArgumentBasenameMatch("libtool", basename_match_cb)
