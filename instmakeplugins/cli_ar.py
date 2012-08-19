# Copyright (c) 2010 by Cisco Systems, Inc.
"""
archive (ar) CLI plugin for instmake
"""

import re
import sys
from instmakelib import clibase
from instmakelib import instmake_log as LOG

description = "Analyze ar commands"

name = "ar"

def usage():
    print "\tunordered : The order of the inputs doesn't matter"

members_order_matter = 1
def UserOption(option):
    global members_order_matter

    if option == "unordered":
        members_order_matter = 0
        print name, ": The order of the inputs doesn't matter"
    else:
        print >> sys.stderr, option, "not supported"
        sys.exit(1)

class Archive(clibase.CLIPluginBase):

    plugin_name = "ar"

    def __init__(self, args, cwd, pathfunc):
        clibase.CLIPluginBase.__init__(self)

        self.ar = args[0]
        self.members = []
        self.archive_file = None
        self.operations = []
        self.relpos = None
        self.count = None

        valid_operations = "dmpqrtx"
        valid_modifiers = "abcfilNoPsSuvV"
        modifiers_that_take_relpos = "abi"
        modifiers_that_take_count = "N"

        STATE_OPERATION = 0
        STATE_ARCHIVE = 1
        STATE_MEMBER = 2
        STATE_RELPOS = 3
        STATE_COUNT = 4

        state = STATE_OPERATION
        need_relpos = 0
        need_count = 0

        for arg in args[1:]:
            if state == STATE_OPERATION:
                # Examine each character:
                for c in arg:
                    if c in valid_operations or c in valid_modifiers:
                        self.operations.append(c)

                        if c in modifiers_that_take_count:
                            need_count = 1

                        if c in modifiers_that_take_relpos:
                            need_relpos = 1

                    else:
                        raise clibase.BadCLIException("cli_ar: '%s' operation/modifer not expected." % (c,))

                if need_relpos:
                    state = STATE_RELPOS
                elif need_count:
                    state = STATE_COUNT
                else:
                    state = STATE_ARCHIVE

            elif state == STATE_RELPOS:
                self.relpos = arg
                need_relpos = 0
                if need_count:
                    state = STATE_COUNT
                else:
                    state = STATE_ARCHIVE

            elif state == STATE_COUNT:
                self.count = arg
                need_count = 0
                state = STATE_ARCHIVE

            elif state == STATE_ARCHIVE:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                self.archive_file = path
                state = STATE_MEMBER

            elif state == STATE_MEMBER:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                self.members.append(path)

            else:
                raise clibase.BadCLIException("cli_ar: Unknown state %s" % (state,))

        if not self.archive_file:
            raise clibase.NotHandledException

    def AdjustFiles(self, callback):
        self.archive_file = callback(self.archive_file)
        self.members = map(callback, self.members)

    def Outputs(self):
        return [self.archive_file]

    def Dump(self):
        print "Ar Binary:          ", self.ar
        print "Operations/Modifiers:", self.operations
        print "Archive File:       ", self.archive_file
        print "Members:            ", self.members
        if self.relpos:
            print "Relpos:             ", self.relpos
        if self.count:
            print "Count:              ", self.count


    def Compare(self, other, dir, my_file, other_file, collator):
        """Returns 1 if no problems were found, 0 if problems were found."""
        ok = 1

        ok *= self.CompareValue(dir, my_file, other_file, self.ar, other.ar, "Ar Binary",
                collator)

        # Use Oordered or Unordered
        if members_order_matter:
            ok *= self.CompareOrderedList(dir, my_file, other_file,
                self.members, other.members, "Members (ordered)",
                collator)
        else:
            ok *= self.CompareUnorderedList(dir, my_file, other_file,
                self.members, other.members, "Members (unordered)",
                collator)

        ok *= self.CompareValue(dir, my_file, other_file, self.archive_file,
                other.archive_file, "Archive file", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.operations, other.operations, "Operations/Modifiers", collator)

        ok *= self.CompareValue(dir, my_file, other_file, self.relpos, other.relpos,
                "Relpos", collator)
        ok *= self.CompareValue(dir, my_file, other_file, self.count, other.count,
                "Count", collator)

        return ok


def create_parser(cmdline_args, cwd, pathfunc):
    return Archive(cmdline_args, cwd, pathfunc)

def register(manager):
    manager.RegisterToolRegex(create_parser, re.compile(r"^ar$"))
    manager.RegisterToolRegex(create_parser, re.compile(r"^ar\."))
