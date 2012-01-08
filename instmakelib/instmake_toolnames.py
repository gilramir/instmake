# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Manage the tool plugins and use them appropriately.
"""
import os

TOOLNAME_PLUGIN_PREFIX = "toolname"

class ToolNameManager:
    """ToolName plugins have to register with this manager
    the circumstances under which they wish to be called."""
    def __init__(self, plugins):
        toolname_plugins = plugins.LoadAllPlugins(TOOLNAME_PLUGIN_PREFIX)

        self.first_arg_matches = []
        self.first_arg_basename_matches = []

        self.first_arg_regexes= []
        self.first_arg_basename_regexes = []
        self.command_line_regexes = []

        for plugin in toolname_plugins:
            plugin.register(self)

    def RegisterFirstArgumentMatch(self, text, cb):
        """Call back parameters: first_arg, argv, cwd"""
        self.first_arg_matches.append((text, cb))

    def RegisterFirstArgumentRegex(self, regex, cb):
        """Call back parameters: first_arg, argv, cwd, regex_match"""
        self.first_arg_regexes.append((regex, cb))

    def RegisterFirstArgumentBasenameMatch(self, text, cb):
        """Call back parameters: basename, first_arg, argv, cwd"""
        self.first_arg_basename_matches.append((text, cb))

    def RegisterFirstArgumentBasenameRegex(self, regex, cb):
        """Call back parameters: basename, first_arg, argv, cw, regex_match"""
        self.first_arg_basename_regexes.append((regex, cb))

    def RegisterCommandLineRegex(self, regex, cb):
        """Call back parameters: argv, cwd, regex_match"""
        self.command_line_regexes.append((regex, cb))

    def GetTool(self, cmdline_args, cwd):
        """Returns a single string representing the tool in this
        command-line. cmdline_args is an array of strings that will
        be concatenated with spaces to form a single command-line."""

        # It's done this way because of the way the command-line is
        # stored in the instmake log. The top-most process (which is
        # the first 'make' run, i.e., the last record in the instmake log)
        # has a cmdline_args with one true argv-item per item. However,
        # the instmakes that were called from 'make' have their entire
        # command-line existing as a single string (the first and only
        # item in cmdline_args).
        argv_joined = ' '.join(cmdline_args)
        argv = argv_joined.split()

        # Call _GetTool as many times as necessary to find
        # a non-changing answer.
        seen = {}
        max_iterations = 100
        i = 0

        while 1:
            seen[argv_joined] = None
            new_argv = self._GetTool(argv, cwd)
            new_argv_joined = ' '.join(new_argv)

            if new_argv_joined == argv_joined:
                return new_argv[0]
            elif seen.has_key(new_argv_joined):
                return new_argv[0]
            else:
                i += 1
                if i == max_iterations:
                    return new_argv[0]
                argv = new_argv
                argv_joined = new_argv_joined

    def _GetTool(self, argv, cwd):
        cmdline = ' '.join(argv) 
        # Check the command-line
        for (regex, cb) in self.command_line_regexes:
            m = regex.search(cmdline)
            if m:
                retval = cb(argv, cwd, m)
                if retval != None:
                    return retval

        # Get the first argument
        if len(argv) >= 1:
            first_arg = argv[0]
        else:
            return argv

        # Check the first argument
        for (text, cb) in self.first_arg_matches:
            if first_arg == text:
                retval =  cb(first_arg, argv, cwd)
                if retval != None:
                    return retval

        for (regex, cb) in self.first_arg_regexes:
            m = regex.search(first_arg)
            if m:
                retval = cb(first_arg, argv, cwd, m)
                if retval != None:
                    return retval

        # Check the basename of the first arg
        basename = os.path.basename(first_arg)
        for (text, cb) in self.first_arg_basename_matches:
            if basename == text:
                retval = cb(basename, first_arg, argv, cwd)
                if retval != None:
                    return retval

        for (regex, cb) in self.first_arg_basename_regexes:
            m = regex.search(basename)
            if m:
                retval = cb(basename, first_arg, argv, cwd, m)
                if retval != None:
                    return retval

        # Nothing matched. Return the default value.
        return argv
