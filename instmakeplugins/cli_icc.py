# Copyright (c) 2010, by Cisco Systems, Inc.
"""
icc CLI plugin for instmake
"""

import os
from instmakelib import clibase
from instmakelib import instmake_log as LOG
import re

description = "Analyze icc commands"

name = "icc"

def usage():
    pass

def UserOption(option):
    pass

class ICC(clibase.CLIPluginBase):

    plugin_name = "icc"

    def __init__(self, args, cwd, pathfunc):
        clibase.CLIPluginBase.__init__(self)

        self.compiler = args[0]
        self.toggle_flags = []
        self.sources = []
        self.cfgs = []
        self.outputs = []

        self.I_paths = []
        self.include_paths = []
        self.imacros_paths = []
        self.isystem_paths = []
        self.pe_file_prefix_paths = []
        self.gcc_name = []
        self.gcc_version = []
        self.defines = []
        self.undefines = []
        self.libs = []
        self.L_paths = []

        # An argument followed by another argument that is a file path
        path_next_hash = {
            "-I" : self.I_paths,
            "-include" : self.include_paths,
            "-imacros" : self.imacros_paths,
            "-isystem" : self.isystem_paths,
            "-L" : self.L_paths,
        }

        # An argument with a path argument attached to it directly w/o any
        # equal sign (or space!). Each record is:
        # (option string, len(option string), array where to store value)
        path_adjoined_table = (
            ("-I", 2, self.I_paths),
            ("-isystem", 8, self.imacros_paths),
        )

        # One argument that has a LHS, an equal sign, and a RHS that
        # is a file path.
        path_eq_adjoined_hash = {
            "-pe-file-prefix" : self.pe_file_prefix_paths,
        }

        # One argument that has a LHS, an equal sign, and a RHS that
        # is NOT a file path.
        value_eq_adjoined_hash = {
            "-gcc-name" : self.gcc_name,
            "-gcc-version" : self.gcc_version,
        }

        # An argument that has a path attached to it 

        # One argument that has a dash, a single character, and then
        # a value that is NOT a path. The entire argument (not just the
        # part after the dash and single character) is added to
        # self.toggle_flags. 
        single_char_toggle_value_adjoined_tuple = (
            "-f",
            "-O",
            "-W",
            "-w",
        )

        # One argument that has a dash, a single character, and then
        # a value that is NOT a path. The value after the dash and
        # single character is appended to the list.
        single_char_value_only_adjointed_hash = {
            "-D": self.defines,
            "-l": self.libs,
            "-U": self.undefines,
        }
   
        # Boolean flags that do not have any arguments after them
        valid_toggle_flags = [
            "-c",
            "-dynamic-runtime-data-init",
            "-multiline-strings",
            "-nostdinc",
            "-pipe",
            "-print-search-dirs",
            "-size-llp64",
            "-x",
        ]

        # Toggle flags with no argument after them, but that need regexes
        # to match. Each item here should be a compiled regex object.
        regex_toggle_flags = []

        stdout_dups = [ "1>&2", "&>" ]
        end_of_cmd = ["|"]

        STATE_NORMAL = 0
        STATE_PATH_NEXT = 1
        STATE_MF = 2
        STATE_o = 3

        state = STATE_NORMAL

        # Is -MF used to change the name of the .d ?
        mf_used = False

        # Will a .d be created, using the default name?
        create_default_dotd_name = False

        # Was there a -o option?
        dot_o_used = False

        for arg in args[1:]:
            # Is there an embedded equals sign?
            i = arg.find("=")
            if i >= 1:
                arg_lhs = arg[:i]
                arg_rhs = arg[i+1:]
            else:
                arg_lhs = ""
                arg_rhs = ""

            if state == STATE_NORMAL:
                if arg in valid_toggle_flags:
                    self.toggle_flags.append(arg)

                elif arg[0] == "@":
                    path = LOG.normalize_path(arg[1:], cwd)
                    if pathfunc:
                        path = pathfunc(path)
                    self.cfgs.append(path)

                elif path_next_hash.has_key(arg):
                    state = STATE_PATH_NEXT
                    path_next_array = path_next_hash[arg]

                elif path_eq_adjoined_hash.has_key(arg_lhs):
                    path = LOG.normalize_path(arg_rhs, cwd)
                    if pathfunc:
                        path = pathfunc(path)
                    path_eq_adjoined_hash[arg_lhs].append(path)

                elif value_eq_adjoined_hash.has_key(arg_lhs):
                    value_eq_adjoined_hash[arg_lhs].append(arg_rhs)

                elif len(arg) >= 2 and arg[:2] in \
                    single_char_toggle_value_adjoined_tuple:
                    self.toggle_flags.append(arg)

                elif len(arg) >= 2 and \
                        single_char_value_only_adjointed_hash.has_key(arg[:2]):
                    single_char_value_only_adjointed_hash[arg[:2]].append(arg[2:])

                elif arg == "-MD":
                    if not mf_used:
                        create_default_dotd_name = True
                    self.toggle_flags.append(arg)

                elif arg == "-MF":
                    # This works for -MD -MF, but -MF -MD will fail,
                    # so set mf_used
                    mf_used = True
                    create_default_dotd_name = False
                    self.toggle_flags.append(arg)
                    state = STATE_MF

                elif arg == "-o":
                    state = STATE_o

                elif arg[0] == "-":
                    # Path adjoined to option?
                    for (opt, len_opt, values) in path_adjoined_table:
                        if len(arg) > len_opt and arg[:len_opt] == opt:
                            path = LOG.normalize_path(arg[len_opt:], cwd)
                            values.append(path)
                            break
                    else:
                        # Regex?
                        for regex_flag in regex_toggle_flags:
                            m = regex_flag.match(arg)
                            if m:
                                self.toggle_flags.append(arg)
                                break
                        else:
                            raise clibase.BadCLIException("cli_icc: unknown option: %s\n%s" % (arg, args))

                elif arg in stdout_dups:
                    continue

                elif arg in end_of_cmd:
                    break
               
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

            elif state == STATE_MF:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                self.outputs.append(path)
                state = STATE_NORMAL

            elif state == STATE_o:
                path = LOG.normalize_path(arg, cwd)
                if pathfunc:
                    path = pathfunc(path)
                self.outputs.append(path)
                state = STATE_NORMAL
                dot_o_used = True

        if not self.sources:
            raise clibase.NotHandledException

        # If "-o" was not used, still try to figure out an output file.
        if not dot_o_used:
            # Check filenames if we're *not* preprocessing.
            if "-E" in self.toggle_flags or \
                    "-M" in self.toggle_flags or \
                    "-MM" in self.toggle_flags:
                output = "<STDOUT>"
            else:
                source = os.path.basename(self.sources[0])
                if len(source) <= 2:
                    raise clibase.BadCLIException("cli_icc: Source file %s has too short name." % (source,))

                src_root, src_ext = os.path.splitext(source)
                output = src_root + ".o"
                if src_ext == "":
                    raise clibase.BadCLIException("cli_icc: Source file %s does not end with dot-something." \
                        % (source,))

            path = LOG.normalize_path(output, cwd)
            if pathfunc:
                path = pathfunc(path)

            self.outputs.append(path)

        if create_default_dotd_name:
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

        if not self.outputs:
            raise clibase.NotHandledException


    def Dump(self):
        print "Compiler:           ", self.compiler
        print "Outputs:            ", self.outputs
        print "Sources:            ", self.sources
        print "Configs:            ", self.cfgs
        print "Toggle-flags:       ", self.toggle_flags
        print "-D flags:           ", self.defines
        print "-U flags:           ", self.undefines
        print "Libs:               ", self.libs
        print "-I flags:           ", self.I_paths
        print "-L flags:           ", self.L_paths
        print "-imacros flags:     ", self.imacros_paths
        print "-isystem flags:     ", self.isystem_paths
        print "-include flags:     ", self.include_paths

    def Compare(self, other, dir, my_file, other_file, collator):
        """Returns 1 if no problems were found, 0 if problems were found."""
        ok = 1

        ok *= self.CompareValue(dir, my_file, other_file, self.compiler, other.compiler, "Compilers", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.outputs, other.outputs, "Outputs", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.sources, other.sources, "Sources", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.cfgs, other.cfgs, "Configs", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.toggle_flags, other.toggle_flags, "Toggle flags", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.defines, other.defines, "-D flags", collator)

        ok *= self.CompareUnorderedList(dir, my_file, other_file,
            self.undefines, other.undefines, "-U flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.libs, other.libs, "Libraries", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.I_paths, other.I_paths, "-I flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.L_paths, other.L_paths, "-L flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.imacros_paths, other.imacros_paths, "-imacros flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.isystem_paths, other.isystem_paths, "-isystem flags", collator)

        ok *= self.CompareOrderedList(dir, my_file, other_file,
            self.include_paths, other.include_paths, "-include flags", collator)

        return ok


def icc_parser(cmdline_args, cwd, pathfunc):
    parser = ICC(cmdline_args, cwd, pathfunc)
    return parser

def register(manager):
    manager.RegisterToolRegex(icc_parser, re.compile(r"^icc$"))
    manager.RegisterToolRegex(icc_parser, re.compile(r"^icc\."))
