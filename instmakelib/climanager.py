# Copyright (c) 2010 by Cisco Systems, Inc.
"""
CLI Plugin Manager
"""
from instmakelib import instmake_log as LOG
from instmakelib import shellsyntax
from instmakelib import clibase
import sys

class CLIManager:
    """Manages the CLI plugins."""

    def __init__(self, plugins=None):
        # Load CLI plugins
        if not plugins:
            plugins = LOG.GetPlugins()
        mods = plugins.LoadAllPlugins(LOG.CLI_PLUGIN_PREFIX)
       
        # Containers for CLI plugins to register themselves to.
        self.tool_contains = []
        self.tool_regexes = []

        # Key = 'name' from plugin, Value = plugin module
        self.plugin_names = {}

        for mod in mods:
            mod.register(self)
            self.plugin_names[mod.name] = mod

    def PrintHelp(self):
        names = self.plugin_names.keys()
        names.sort()
        for name in names:
            mod = self.plugin_names[name]
            print name, ":", mod.description
            mod.usage()


    def UserOption(self, user_option):
        i = user_option.find(",")
        if i < 1:
            sys.exit("Invalid CLI plugin option: %s" % (user_option,))

        plugin_name = user_option[:i]
        option_text = user_option[i+1:]
        options = option_text.split(",")

        if not self.plugin_names.has_key(plugin_name):
            sys.exit("No CLI plugin '%s'" % (plugin_name,))

        mod = self.plugin_names[plugin_name]
        for option in options:
            mod.UserOption(option)

    def _ParseCmdline(self, cmdline_string):
        cmdline_args = shellsyntax.split_shell_cmdline(cmdline_string)

        # XXX - We need to be able to handle "segmented" command-lines
        # (using &&, ||, ;, and the redirection symbols). But we don't
        # have a full-blown shell-cmdline parser. For now, we can help
        # the cli plugins if we tidy things up a bit.
        if cmdline_args:
            # Remove any prefixed new-lines, which can come in from
            # make-3.81
            cmdline_args = [a.lstrip("\n") for a in cmdline_args]

            # Look for a word that stars with `, like `gcc.....  ...`
            for i, arg in enumerate(cmdline_args):
                if len(arg) > 1 and arg[0] == "`":
                    cmdline_args = cmdline_args[:i]

            if ";" in cmdline_args:
                i = cmdline_args.index(";")
                cmdline_args = cmdline_args[:i]

            if "||" in cmdline_args:
                i = cmdline_args.index("||")
                cmdline_args = cmdline_args[:i]

            if "&&" in cmdline_args:
                i = cmdline_args.index("&&")
                cmdline_args = cmdline_args[:i]

            # Trailing semicolon attached to a word
            if cmdline_args[-1] == ";":
                cmdline_args = cmdline_args[:-1]

            # make-3.81 will put a trailing backslash ("\\n") in the cmdline,
            # which shows up as \n; after the previous filter, it will now
            # be an empty string, so remove that here.
            cmdline_args = filter(lambda x: x != "", cmdline_args)

        return cmdline_args


    def ParseRecord(self, rec, cwd=None, pathfunc=None):
        """Find a Parser object that can parse the command-line in the
        log record."""
        cmdline_args = self._ParseCmdline(rec.cmdline)

        # Check tool regexes
        for (regex, cb) in self.tool_regexes:
            if rec.tool != None and regex.search(rec.tool):
                if cwd == None:
                    cwd = rec.cwd

                try:
                    retval = cb(cmdline_args, cwd, pathfunc)
                    return retval
                except clibase.NotHandledException:
                    return None
                except clibase.BadCLIException, err:
                    print >> sys.stderr, "Error in PID %s" % (rec.pid,)
                    print >> sys.stderr, err
                    rec.Print(sys.stderr)
                    sys.exit(1)

        # Check tool substrings
        for (substring, cb) in self.tool_contains:
            if rec.tool != None and rec.tool.find(substring) > -1:
                if cwd == None:
                    cwd = rec.cwd

                try:
                    retval = cb(cmdline_args, cwd, pathfunc)
                    return retval
                except clibase.NotHandledException:
                    return None
                except clibase.BadCLIException, err:
                    print >> sys.stderr, "Error in PID %s" % (rec.pid,)
                    print >> sys.stderr, err
                    rec.Print(sys.stderr)
                    sys.exit(1)

        # Nothing matched. Return None for "no parser"
        return None


    # Methods a CLI plugin can call to register itself.
    def RegisterToolContains(self, cb, substring):
        self.tool_contains.append((substring, cb))

    def RegisterToolRegex(self, cb, regex):
        self.tool_regexes.append((regex, cb))
