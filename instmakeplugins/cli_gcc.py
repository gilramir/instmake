# Copyright (c) 2010 by Cisco Systems, Inc.
"""
gcc CLI plugin for instmake
"""

import os
from instmakelib import clibase
from instmakelib import instmake_log as LOG
import re
import sys

description = "Analyze gcc commands"

name = "gcc"

IGNORE_I = "ignore-I"

def usage():
    print "\tignore-I                  : Ignore -I paths"
    print "\tWp                        : Some -Wp,* options are treated as non-Wp"
    print "\tignore-WpMT               : Ignore -Wp,-Mt options"
    print "\tignore-I-with/<substring> : Ignore -I containing <substring>"
    print "\tdso-num-trim              : DSO numbers match w/o leading 0's"
    print "\tignore-W/<string>         : Ignore -W<string> flags"

ignore_Ipaths = 0
Wp_options = 0
ignore_WpMT = False
ignore_I_with = []
ignore_W = []
dso_number_trim = False

def UserOption(option):
    global ignore_Ipaths
    global Wp_options
    global ignore_WpMT
    global dso_number_trim

    if option == "ignore-I":
        ignore_Ipaths = 1
        print name, ": Ignoring -I paths"
    elif option == "Wp":
        Wp_options = 1
        print name, ": Some -Wp,* options are treated as non-Wp"
    elif option == "ignore-WpMT":
        ignore_WpMT = True
        print name, ": Ignore -Wp,-MT options"
    elif option[0:14] == "ignore-I-with/":
        ignore_I_with.append(option[14:])
        print name, ": Ignore -I with:", option[14:]
    elif option[0:9] == "ignore-W/":
        ignore_W.append(option[9:])
        print name, ": Ignore -W", option[9:]
    elif option == "dso-number-trim":
        dso_number_trim = True
        print name, ": DSO numbers match w/o leading 0's"
    else:
        print >> sys.stderr, option, "not supported"
        sys.exit(1)


class GCC(clibase.CLIPluginBase):

    plugin_name = "gcc"

    def __init__(self, args, cwd, pathfunc):
        clibase.CLIPluginBase.__init__(self)

        start_arg = 0
        if args[0] == "dcache":
            start_arg = 1

        self.compiler = args[start_arg]
        self.toggle_flags = []
        self.sources = []
        self.gnum = None
        self.defines = []
        self.undefines = []
        self.libs = []
        self.I_paths = []
        self.L_paths = []
        self.imacro_paths = []
        self.idirafter_paths = []
        self.iwithprefix_paths = []
        self.include_paths = []
        self.linker_scripts = []
        self.entry_symbol = None
        self.print_file_name = None
        self.section_starts = {}
        self.xlinker_args = []
        self.params = []
        self.linker_undefined_symbols = []

        STATE_NORMAL = 0
        STATE_G = 1
        STATE_o = 2
        STATE_PATH_NEXT = 3
        STATE_e = 4
        STATE_Tsection = 5
        STATE_D = 6
        STATE_I = 7
        STATE_x = 8
        STATE_Xlinker = 9
        STATE_MF = 10
        STATE_param = 11
        STATE_u = 12

        path_next_array = None

        dot_o_used = 0
        default_dotd_name = 0
        mf_used = 0 
        next_Wp_is_dotd = 0
        section_for_section_start = None

        path_next_hash = {
            "-I" : self.I_paths,
            "-imacros" : self.imacro_paths,
            "-idirafter" : self.idirafter_paths,
            "-iwithprefix" : self.iwithprefix_paths,
            "-include" : self.include_paths,
            "-L" : self.L_paths,
            "-T" : self.linker_scripts,
        }
        path_next = path_next_hash.keys()
    
        valid_toggle_flags = [
            "-Bdynamic",
            "-c",
            "-dD",
            "-dM",
            "-dN",
            "-g",
            "-gcoff",
            "-gstabs+",
            "-idrop-leading-space",
            "-isimplify-pathnames",     # Cisco gcc
            "-E",
            "-EB",
            "-M",
            "-MG",
            "-MM",
            "-MMD",
            "-N",           # linker option
            "-O",
            "-P",
            "-non_shared",
            "-nostdinc",
            "-nostdinc++",
            "-nostdlib",
            "--no-warn-mismatch",
            "-undef",
            "-nocpp",
            "-pipe",
            "--print-libgcc",
            "-print-libgcc-file-name",
            "-r",           # linker option
            "-S",
            "-static",
            "-v",
            "--version",
            "-w",
        ]

        # All these must start with "-" because of the place
        # where regex_toggle_flags is checked.
        regex_toggle_flags = [
                re.compile(r"-g\d"),
                re.compile(r"-ggdb\d"),
                re.compile(r"-gstabs\d"),
                re.compile(r"-gcoff\d"),
                re.compile(r"-gxcoff\d"),
                re.compile(r"-gvms\d"),
        ]

        stdout_dups = [ "1>&2", "&>" ]

        state = STATE_NORMAL
        next_Wp_is_doto = False
        ignore_next_Wp = False

        for arg in args[start_arg+1:]:
            if state == STATE_NORMAL:
                if arg in valid_toggle_flags:
                    self.toggle_flags.append(arg)

                elif len(arg) >= 2 and arg[:2] == "-O":
                    self.toggle_flags.append(arg)

                elif len(arg) >= 18 and arg[:18] == "--print-file-name=":
                    self.print_file_name = arg[18:]

                elif len(arg) >= 17 and arg[:17] == "-print-file-name=":
                    self.print_file_name = arg[17:]

                elif len(arg) > 4 and arg[:4] == "-Wp,":
                    if ignore_next_Wp:
                        ignore_next_Wp = False

                    elif next_Wp_is_dotd or next_Wp_is_doto:
                        path = LOG.normalize_path(arg[4:], cwd)
                        if pathfunc:
                            path = pathfunc(path)
                        # -Wp,-MT -Wp,foo.o means we write foo.d
                        # so we have to change the .o name to a .d name
                        if next_Wp_is_doto:
                            # do nothing with it for now.
                            pass
#                            root, ext = os.path.split(path)
#                            if ext == ".o":
#                                path = root + ".d"
                        else:
                            self.outputs.append(path)
                        next_Wp_is_dotd = 0
                        next_Wp_is_doto = False

                    elif arg == "-Wp,-MD":
                        if Wp_options:
                            self.toggle_flags.append(arg[4:])
                        else:
                            self.toggle_flags.append(arg)
                        next_Wp_is_dotd = 1

                    elif arg == "-Wp,-MT":
                        if not ignore_WpMT:
                            self.toggle_flags.append(arg)
                            ignore_next_Wp = True
                        next_Wp_is_doto = True

                    else:
                        self.toggle_flags.append(arg)

                elif len(arg) >= 2 and arg[:2] == "-W":
                    flag = arg[2:]
                    for ignore in ignore_W:
                        if flag == ignore:
                            break
                    else:
                        self.toggle_flags.append(arg)

                elif len(arg) >= 2 and arg[:2] == "-f":
                    self.toggle_flags.append(arg)

                elif len(arg) >= 2 and arg[:2] == "-m":
                    self.toggle_flags.append(arg)

                elif len(arg) > 2 and arg[0:2] == "-l":
                    self.libs.append(arg[2:])

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

                elif arg == "-o":
                    state = STATE_o

                elif arg == "-G":
                    state = STATE_G

                elif arg == "-e":
                    state = STATE_e

                elif arg == "-D":
                    state = STATE_D

                elif arg == "-I":
                    state = STATE_I

                elif arg == "-Xlinker":
                    state = STATE_Xlinker

                elif arg == "--param":
                    state = STATE_param

                # Can be "-x ARG" or "-xARG"
                elif arg == "-x":
                    state = STATE_x

                elif arg == "-u":
                    state = STATE_u

                elif len(arg) > 2 and arg[:2] == "-x":
                    self.toggle_flags.append(arg)


                elif arg == "-MD":
                    if not mf_used:
                        default_dotd_name = 1
                    self.toggle_flags.append(arg)

                elif arg == "-MF":
                    # This works for -MD -MF, but -MF -MD will fail,
                    # so set mf_used
                    mf_used = 1
                    default_dotd_name = 0
                    self.toggle_flags.append(arg)
                    state = STATE_MF

                elif arg in path_next:
                    state = STATE_PATH_NEXT
                    path_next_array = path_next_hash[arg]

                elif len(arg) > 2 and arg[0:2] == "-G":
                    self.gnum = arg[2:]

                elif len(arg) > 2 and arg[0:2] == "-I":
                    path = LOG.normalize_path(arg[2:], cwd)
                    if pathfunc:
                        path = pathfunc(path)
                    for ignore in ignore_I_with:
                        if ignore in path:
                            break
                    else:
                        self.I_paths.append(path)

                elif len(arg) > 2 and arg[0:2] == "-L":
                    path = LOG.normalize_path(arg[2:], cwd)
                    if pathfunc:
                        path = pathfunc(path)
                    self.L_paths.append(path)

                elif len(arg) > 2 and arg[0:2] == "-D":
                    self.defines.append(arg[2:])

                elif len(arg) > 2 and arg[0:2] == "-U":
                    self.undefines.append(arg[2:])

                elif arg in self.shell_terminators:
                    break

                elif arg[0] == "-":
                    # Regex?
                    for regex_flag in regex_toggle_flags:
                        m = regex_flag.match(arg)
                        if m:
                            self.toggle_flags.append(arg)
                            break
                    else:
                        raise clibase.BadCLIException("cli_gcc: unknown option: %s\n%s" % (arg, args))

                elif arg in stdout_dups:
                    continue
               
                else:
                    path = LOG.normalize_path(arg, cwd)
                    if pathfunc:
                        path = pathfunc(path)
                    self.sources.append(path)

            elif state == STATE_PATH_NEXT:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                path_next_array.append(path)
                state = STATE_NORMAL

            elif state == STATE_G:
                self.gnum = arg
                state = STATE_NORMAL

            elif state == STATE_o:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                self.outputs.append(path)
                state = STATE_NORMAL
                dot_o_used = 1

            elif state == STATE_e:
                self.entry_symbol = arg
                state = STATE_NORMAL

            elif state == STATE_Tsection:
                self.section_starts[section_for_section_start] = arg
                state = STATE_NORMAL

            elif state == STATE_D:
                self.defines.append(arg)
                state = STATE_NORMAL

            elif state == STATE_I:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                for ignore in ignore_I_with:
                    if ignore in path:
                        break
                else:
                    self.I_paths.append(path)
                state = STATE_NORMAL

            elif state == STATE_MF:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                self.outputs.append(path)
                state = STATE_NORMAL

            elif state == STATE_x:
                self.toggle_flags.append("-x" + arg)
                state = STATE_NORMAL

            elif state == STATE_Xlinker:
                self.xlinker_args.append(arg)
                state = STATE_NORMAL

            elif state == STATE_param:
                self.params.append(arg)
                state = STATE_NORMAL

            elif state == STATE_u:
                self.linker_undefined_symbols.append(arg)
                state = STATE_NORMAL

            else:
                raise clibase.BadCLIException("cli_gcc: Unknown state %s" % (state,))

        if not self.sources:
            raise clibase.NotHandledException

        if default_dotd_name:
            # Create the .d file by removing the suffix from
            # the source and adding ".d". Make sure however that
            # a source is not a ".o" file.
            for file in self.sources:
                (root, ext) = os.path.splitext(file)
                basename = os.path.basename(root)
                if ext != ".o":
                    dotd_basename = basename + ".d"
                    path = LOG.normalize_path(dotd_basename, cwd)
                    if pathfunc:
                        path = pathfunc(path)
                    self.outputs.append(path)

        if not dot_o_used:
            if len(self.sources) == 0:
                raise clibase.BadCLIException("cli_gcc: No -o, but %d sources instead of 1." % \
                        (len(self.sources),))

            # Check filenames if we're *not* preprocessing.
            if "-E" in self.toggle_flags or \
                    "-M" in self.toggle_flags or \
                    "-MM" in self.toggle_flags:
                output = "<STDOUT>"
            else:
                source = os.path.basename(self.sources[0])
                if len(source) <= 2:
                    raise clibase.BadCLIException("cli_gcc: Source file %s has too short name." % (source,))

                src_root, src_ext = os.path.splitext(source)
                output = src_root + ".o"
                if src_ext == "":
                    raise clibase.BadCLIException("cli_gcc: Source file %s does not end with dot-something." \
                        % (source,))

            path = LOG.normalize_path(output, cwd)
            if pathfunc:
                path = pathfunc(path)

            self.outputs.append(path)

        if not self.outputs:
            raise clibase.NotHandledException


    def AdjustFiles(self, callback):
        self.outputs = map(callback, self.outputs)
        self.sources = map(callback, self.sources)
        self.linker_scripts = map(callback, self.linker_scripts)
        self.imacro_paths = map(callback, self.imacro_paths)
        self.include_paths = map(callback, self.include_paths)
        self.I_paths = map(callback, self.I_paths)

    def AddDFlag(self, flag):
        if not flag in self.defines:
            self.defines.append(flag)

    def Dump(self):
        print "Compiler:           ", self.compiler
        print "Outputs:            ", self.outputs
        print "Sources:            ", self.sources
        print "Toggle-flags:       ", self.toggle_flags
        print "-G:                 ", self.gnum
        print "-D flags:           ", self.defines
        print "-U flags:           ", self.undefines
        print "Libs:               ", self.libs
        print "-I flags:           ", self.I_paths
        print "-L flags:           ", self.L_paths
        print "-imacro flags:      ", self.imacro_paths
        print "-idirafter flags:   ", self.idirafter_paths
        print "-iwithprefix flags: ", self.iwithprefix_paths
        print "-include flags:     ", self.include_paths
        print "Linker scripts:     ", self.linker_scripts
        print "Entry symbol:       ", self.entry_symbol
        print "Printed File Name:  ", self.print_file_name
        print "-Xlinker args:      ", self.xlinker_args
        print "--param args:       ", self.params
        print "-u symbols:         ", self.linker_undefined_symbols

        if self.section_starts:
            for (section, start) in self.section_starts.items():
                print "Section:              ", section, "starts at", start


    def Compare(self, other, dir, my_file, other_file, collator):
        """Returns 1 if no problems were found, 0 if problems were found."""
        ok = 1

        ok *= self.CompareValue(dir, my_file, other_file, self.compiler, other.compiler, "Compilers", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.outputs, other.outputs, "Outputs", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.sources, other.sources, "Sources", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.toggle_flags, other.toggle_flags, "Toggle flags", collator)

        ok *= self.CompareValue(dir, my_file, other_file, self.gnum, other.gnum, "G numbers", collator)

        # XXX - -D is unordered, and -U is unordered, but there should be
        # some order *between* -D and -U, in case we -D and -U the
        # same symbol.
        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.defines, other.defines, "-D flags", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.undefines, other.undefines, "-U flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.libs, other.libs, "Libraries", collator)

        if not ignore_Ipaths:
            ok *= self.CompareOrderedList(dir, my_file, other_file,
                self.I_paths, other.I_paths, "-I flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.L_paths, other.L_paths, "-L flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.imacro_paths, other.imacro_paths, "-imacro flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.idirafter_paths, other.idirafter_paths, "-idirafter flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.iwithprefix_paths, other.iwithprefix_paths, "-iwithprefix flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.include_paths, other.include_paths, "-include flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.linker_scripts, other.linker_scripts, "linker scripts", collator)

        ok *= self.CompareValue(dir, my_file, other_file,
            self.entry_symbol, other.entry_symbol, "entry symbol", collator)

        ok *= self.CompareValue(dir, my_file, other_file,
            self.print_file_name, other.print_file_name, "printed file name", collator)

        ok *= self.CompareHashOfValues(dir, my_file, other_file,
            self.section_starts, other.section_starts, "-T<section> starts", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.xlinker_args, other.xlinker_args, "Xlinker args", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.params, other.params, "--param args", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.linker_undefined_symbols, other.linker_undefined_symbols,
            "-u symbols", collator)

        return ok

def gcc_parser(cmdline_args, cwd, pathfunc):
    parser = GCC(cmdline_args, cwd, pathfunc)
    if dso_number_trim:
        parser.AdjustFiles(clibase.dso_trim)
    return parser

def register(manager):
    manager.RegisterToolRegex(gcc_parser, re.compile(r"^cc$"))
    manager.RegisterToolRegex(gcc_parser, re.compile(r"^cc\."))
    manager.RegisterToolRegex(gcc_parser, re.compile(r"^gcc$"))
    manager.RegisterToolRegex(gcc_parser, re.compile(r"^gcc\."))
