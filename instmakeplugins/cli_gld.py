# Copyright (c) 2010 by Cisco Systems, Inc.
"""
gld CLI plugin for instmake
"""

import re
import sys
from instmakelib import clibase
from instmakelib import instmake_log as LOG

description = "Analyze gld commands"
name = "gld"

def usage():
    print "\tunordered                 : The order of the inputs doesn't matter"
    print "\tdso-num-trim              : DSO numbers match w/o leading 0's"

inputs_order_matter = 1
dso_number_trim = False

def UserOption(option):
    global inputs_order_matter
    global dso_number_trim

    if option == "unordered":
        inputs_order_matter = 0
        print name, ": The order of the inputs doesn't matter"
    elif option == "dso-number-trim":
        dso_number_trim = True
        print name, ": DSO numbers match w/o leading 0's"
    else:
        print >> sys.stderr, option, "not supported"
        sys.exit(1)

class GLD(clibase.CLIPluginBase):

    plugin_name = "gld"

    def __init__(self, args, cwd, pathfunc):
        clibase.CLIPluginBase.__init__(self)

        start_arg = 0
        if args[0] == "scache":
            start_arg = 1
        self.linker = args[start_arg]
        self.inputs = []
        self.gnum = None
        self.soname = None
        self.toggle_flags = []
        self.linker_scripts = []
        self.linker_dirs = []
        self.section_starts = {}
        self.entry_symbol = None
        self.sonames = []
        self.maps = []
        self.libs = []
        self.format = None
        self.sysroot = []
        self.rpath_link = []
        self.version_script = []

        valid_toggle_flags = [
            "-Bdynamic",
            "--cref",
            "--dynamic-linker",     # ??? toggle?
            "--emit-relocs",
            "-export-dynamic",
            "-fpic",
            "-g",
            "-r",
            "--more-phdrs",
            "-nostdlib",
            "-no-keep-memory",
            "-no-warn-mismatch",
            "--no-warn-mismatch",
            "--no-whole-archive",  # XXX - not really toggle
            "-n",
            "--nmagic",
            "-N",
            "--omagic",
            "--no-omagic",
            "-relax",
            "--relax",
            "-static",
            "-shared",
            "-u_start",
            "-umain",
            "-e_start",
            "-EB",
            "-v",
            "--verbose",
            "--whole-archive",  # XXX - not really toggle
        ]

        path_next_array = None
        path_next_hash = {
            "-T" : self.linker_scripts,
            "-L" : self.linker_dirs,
            "-soname" : self.sonames,
            "-Map" : self.maps,
            "-rpath-link" : self.rpath_link,
            "--version-script" : self.version_script,
        }

        path_adjoined_hash = {
            "--sysroot" : self.sysroot,
        }
            
        STATE_NORMAL = 0
        STATE_G = 1
        STATE_o = 2
        STATE_Tsection = 3
        STATE_e = 4
        STATE_PATH_NEXT = 5
        STATE_format = 6

        state = STATE_NORMAL

        for arg in args[start_arg+1:]:
            if state == STATE_NORMAL:
                # Is there an embedded equals sign?
                i = arg.find("=")
                if i >= 1:
                    arg_lhs = arg[:i]
                    arg_rhs = arg[i+1:]
                else:
                    arg_lhs = ""
                    arg_rhs = ""

                if arg in valid_toggle_flags:
                    self.toggle_flags.append(arg)

                elif arg == "-G":
                    state = STATE_G

                elif arg == "-o":
                    state = STATE_o

                elif arg == "-e":
                    state = STATE_e

                elif arg == "-format":
                    state = STATE_format

                elif arg == "--oformat":
                    state = STATE_format

                elif len(arg) > 2 and arg[0:2] == "-l":
                    self.libs.append(arg[2:])

                elif len(arg) > 2 and arg[0:2] == "-L":
                    path = LOG.normalize_path(arg[2:], cwd)
                    if pathfunc:
                        path = pathfunc(path)
                    self.linker_dirs.append(path)

                elif len(arg) > 2 and arg[0:2] == "-e":
                    self.entry_symbol = arg[2:]

                elif len(arg) > 2 and arg[0:2] == "-T":
                    rest = arg[2:]
                    if rest in [ "text", "data", "bss" ]:
                        section_for_section_start = arg[2:]
                        state = STATE_Tsection
                    else:
                        path = LOG.normalize_path(arg[2:], cwd)
                        if pathfunc:
                            path = pathfunc(path)
                        self.linker_scripts.append(path)

                elif path_next_hash.has_key(arg):
                    state = STATE_PATH_NEXT
                    path_next_array = path_next_hash[arg]
                
                elif path_adjoined_hash.has_key(arg_lhs):
                    path = LOG.normalize_path(arg_rhs, cwd)
                    if pathfunc:
                        path = pathfunc(path)
                    path_adjoined_hash[arg_lhs].append(path)

                elif arg in self.shell_terminators:
                    break

                elif arg[0] == "-":
                    raise clibase.BadCLIException("cli_gld: unknown option: %s\n%s" % (arg, args))

                else:
                    path = LOG.normalize_path(arg, cwd)
                    if pathfunc:
                        path = pathfunc(path)
                    self.inputs.append(path)

            elif state == STATE_G:
                self.gnum = arg
                state = STATE_NORMAL

            elif state == STATE_format:
                self.format = arg
                state = STATE_NORMAL

            elif state == STATE_o:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                self.outputs.append(path)
                state = STATE_NORMAL

            elif state == STATE_PATH_NEXT:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                path_next_array.append(path)
                state = STATE_NORMAL

            elif state == STATE_Tsection:
                self.section_starts[section_for_section_start] = arg
                state = STATE_NORMAL

            elif state == STATE_e:
                self.entry_symbol = arg
                state = STATE_NORMAL

            else:
                raise clibase.BadCLIException("cli_gld: Unknown state %s" % (state,))

        if not self.inputs:
            raise clibase.NotHandledException

        if not self.outputs:
            raise clibase.NotHandledException

    def AdjustFiles(self, callback):
        self.outputs = map(callback, self.outputs)
        self.inputs = map(callback, self.inputs)
        self.linker_scripts = map(callback, self.linker_scripts)
        self.linker_dirs = map(callback, self.linker_dirs)
        self.sonames = map(callback, self.sonames)
        self.maps = map(callback, self.maps)

    def Dump(self):
        print "Linker:             ", self.linker
        print "Outputs:            ", self.outputs
        print "Inputs:             ", self.inputs
        print "Toggle-flags:       ", self.toggle_flags
        print "-G:                 ", self.gnum
        print "Linker scripts:     ", self.linker_scripts
        print "Linker dirs:        ", self.linker_dirs
        print "Libs:               ", self.libs
        print "Entry symbol:       ", self.entry_symbol
        print "sonames:            ", self.sonames
        print "Map files:          ", self.maps
        print "format:             ", self.format
        print "sysroot:            ", self.sysroot
        print "rpath_link:         ", self.rpath_link
        print "version script:     ", self.version_script
        if self.section_starts:
            for (section, start) in self.section_starts.items():
                print "Section:              ", section, "starts at", start


    def Compare(self, other, dir, my_file, other_file, collator):
        """Returns 1 if no problems were found, 0 if problems were found."""
        ok = 1

        ok *= self.CompareValue(dir, my_file, other_file, self.linker, other.linker, "linkers", collator)
        ok *= self.CompareValue(dir, my_file, other_file, self.gnum, other.gnum, "G numbers", collator)

        # Use Ordered or Nonordered
        if inputs_order_matter:
            ok *= self.CompareOrderedList(dir, my_file, other_file,
                self.inputs, other.inputs, "Inputs (ordered)", collator)
        else:
            ok *= self.CompareUnorderedList(dir, my_file, other_file,
                self.inputs, other.inputs, "Inputs (unordered)", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.toggle_flags, other.toggle_flags, "Other flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.linker_scripts, other.linker_scripts, "linker scripts", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.linker_dirs, other.linker_dirs, "linker dirs", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.libs, other.libs, "libs", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.sonames, other.sonames, "sonames", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.maps, other.maps, "maps", collator)

        ok *= self.CompareValue(dir, my_file, other_file,
            self.entry_symbol, other.entry_symbol, "entry symbol", collator)

        ok *= self.CompareHashOfValues(dir, my_file, other_file,
            self.section_starts, other.section_starts, "-T<section> starts", collator)

        ok *= self.CompareValue(dir, my_file, other_file,
            self.format, other.format, "format", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.sysroot, other.sysroot, "sysroot", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.rpath_link, other.rpath_link, "rpath link", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.version_script, other.version_script, "version script", collator)

        return ok



def gld_parser(cmdline_args, cwd, pathfunc):
    parser = GLD(cmdline_args, cwd, pathfunc)
    if dso_number_trim:
        parser.AdjustFiles(clibase.dso_trim)
    return parser

def register(manager):
    manager.RegisterToolRegex(gld_parser, re.compile(r"^ld$"))
    manager.RegisterToolRegex(gld_parser, re.compile(r"^ld\."))
    manager.RegisterToolRegex(gld_parser, re.compile(r"^gld$"))
    manager.RegisterToolRegex(gld_parser, re.compile(r"^gld\."))
