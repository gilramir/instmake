# Copyright (c) 2010 by Cisco Systems, Inc.
"""
ToolName plugin to return the name of the perl script.
"""


def basename_match_cb(basename, first_arg, argv, cwd):
    LOOKING_FOR_FIRST_ARG = 0
    LOOKING_FOR_SCRIPT = 1
    END_OF_ARGS = 2

    no_arg_switches = 'aCcnpPsSTtuUvwWX'

    state = LOOKING_FOR_FIRST_ARG
    i = -1
    for arg in argv:
        i += 1
        if state == LOOKING_FOR_FIRST_ARG:
            state = LOOKING_FOR_SCRIPT
            continue

        elif state == LOOKING_FOR_SCRIPT:
            # Is script given on command-line?
            if arg == "-e":
                return [first_arg] + argv[1:]

            # Explicit end of arguments?
            elif arg == "--":
                state = END_OF_ARGS
                continue

            # Look for combination switches (-ne, -pne, -Pe, etc.)
            # that end in 'e'
            elif arg[0] == "-" and len(arg) >= 3:
                if arg[1] in no_arg_switches and arg[-1] == 'e':
                    # Make sure the switches before the last
                    # one are also non-argument switches.
                    num_in_between_switches = 3 - len(arg)
                    i = 0
                    good = 1
                    while i < num_in_between_switches:
                        if not arg[2+i] in no_arg_switches:
                            good = 0
                            break

                    if good:
                        return [first_arg] + argv[1:]

            # Ignore other switches
            elif arg[0] == "-":
                continue

            # Non-switch... it must be the name of the script.
            else:
                # Use the 'arg' as the tool
                return [arg] + argv[i+1:]

        elif state == END_OF_ARGS:
            return [arg] + argv[i+1:]

    # Didn't find a script name.
    return argv



def register(manager):
    manager.RegisterFirstArgumentBasenameMatch("perl5", basename_match_cb)
    manager.RegisterFirstArgumentBasenameMatch("perl", basename_match_cb)
    manager.RegisterFirstArgumentBasenameMatch("perl4", basename_match_cb)
