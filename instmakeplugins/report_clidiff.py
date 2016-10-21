# Copyright (c) 2010 by Cisco Systems, Inc.
"""
CLI Diff
"""

import sys
import os
import getopt
from instmakelib import instmake_cli
from instmakelib import imlib
from instmakelib import instmake_log as LOG
from instmakelib import climanager
from instmakelib import pysets
from instmakelib import jsonconfig

LOG_A = 0
LOG_B = 1
NAME_A = "build 1"
NAME_B = "build 2"

path_normalizer = None

description = "Command-Line Diff"

def usage():
    print "clidiff:", description
    print "\t[-p PID] if 1 log, process CLI for PID from log, and show results"
    print "\t         if 2 logs and 1 -p, find PID in first log and compare"
    print "\t         if 2 logs and 2 -p's, find PIDs in both logs and compare"
    print "\t[-n name] Give a better name to an instmake log (can be given twice)"
    print "\t[--cliopt=plugin,option[,...]] Pass an option to a CLI plugin"
    print "\t[--map1 plugin] use filename mapping for log #1"
    print "\t[--map2 plugin] use filename mapping for log #2"
    print "\t[--ok] Show the files that matched their CLI's correctly"

    plugins = LOG.GetPlugins()

    print
    print "CLI Plugins:"
    print "============"
    plugin_manager = climanager.CLIManager()
    plugin_manager.PrintHelp()

    print
    print "Filemap Plugins:"
    print "================"
    instmake_cli.print_plugin_descriptions(plugins,
            instmake_cli.FILEMAP_PLUGIN_PREFIX)

def report(log_file_names, args):
    global NAME_A
    global NAME_B

    pids = None

    # Command-line options
    optstring = "n:p:u"
    longopts = ["cliopt=", "map1=", "map2=", "ok"]

    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    plugin_manager = climanager.CLIManager()

    plugins = LOG.GetPlugins()
    n_count = 0
    map1 = None
    map2 = None
    show_ok_files = 0
    pids = []

    print "Command-line used:"
    print ' '.join(sys.argv)
    print


    for opt, arg in opts:
        if opt == "-n":
            if n_count == 0:
                NAME_A = arg
                n_count += 1
            elif n_count == 1:
                NAME_B = arg
                n_count += 1
            elif n_count == 2:
                sys.exit("-n option can be given only twice")
        elif opt == "-p":
            pids.append(arg)
        elif opt == "--cliopt":
            plugin_manager.UserOption(arg)
        elif opt == "--ok":
            show_ok_files = 1
        elif opt == "--map1":
            try:
                map1 = plugins.LoadPlugin( instmake_cli.FILEMAP_PLUGIN_PREFIX,
                        arg)
            except ImportError, err:
                sys.exit("unable to import %s-plugin '%s':\n\t%s" % \
                        (instmake_cli.FILEMAP_PLUGIN_PREFIX, arg, err))
        elif opt == "--map2":
            try:
                map2 = plugins.LoadPlugin( instmake_cli.FILEMAP_PLUGIN_PREFIX,
                        arg)
            except ImportError, err:
                sys.exit("unable to import %s-plugin '%s':\n\t%s" % \
                        (instmake_cli.FILEMAP_PLUGIN_PREFIX, arg, err))
        else:
            sys.exit("Unhandled option %s" % (opt,))

    if args:
        usage()
        sys.exit(1)

    # Path normalizer being used?
    if imlib.config.has_key(jsonconfig.CONFIG_CLIDIFF_NORMPATH):
        plugin_name = imlib.config[jsonconfig.CONFIG_CLIDIFF_NORMPATH]
        try:
            module = jsonconfig.load_site_plugin(plugin_name)
            global path_normalizer
            path_normalizer = module.normalize_path
        except Exception, e:
            sys.exit("Unable to import %s: %s" % (plugin_name, e))

    # We need exactly 1 or 2 log files, depending on '-p'
    if len(log_file_names) == 1:
        if map2:
            sys.exit("Can't use --map2 with only one log file.")
        if len(pids) == 0:
            sys.exit("If giving only one log file, at least one -p is needed.")

        do_pids(plugin_manager, log_file_names[0], pids, map1)

    else:
        if len(log_file_names) != 2:
            sys.exit("'clidiff' report uses two log files.")

        do_regular_compare(plugin_manager, log_file_names, map1, map2,
                show_ok_files, pids)

def do_pids(plugin_manager, log_file_name, pid, map1):
    build = Build(log_file_name, plugin_manager, map1)
    build.ReadLogForPIDs(pid)

def do_regular_compare(plugin_manager, log_file_names, map1, map2,
        show_ok_files, pids):
    builds = [None, None]

    if len(pids) > 0:
        pid_a = pids[0]
    else:
        pid_a = None
    
    if len(pids) > 1:
        pid_b = pids[1]
    else:
        pid_b = None

    print
    if pid_a:
        print >> sys.stderr, "Loading PID", pid_a, \
                "from", log_file_names[LOG_A], "as", NAME_A
    else:
        print >> sys.stderr, "Loading", log_file_names[LOG_A], "as", NAME_A
    builds[LOG_A] = Build(log_file_names[LOG_A], plugin_manager, map1)
    builds[LOG_A].ReadLog(pid_a)
    print NAME_A, ":", log_file_names[LOG_A]

    if pid_b:
        print >> sys.stderr, "Loading PID", pid_b, \
                "from", log_file_names[LOG_B], "as", NAME_B
    else:
        print >> sys.stderr, "Loading", log_file_names[LOG_B], "as", NAME_B
    builds[LOG_B] = Build(log_file_names[LOG_B], plugin_manager, map2)
    builds[LOG_B].ReadLog(pid_b)
    print NAME_B, ":", log_file_names[LOG_B]
    print

    print >> sys.stderr, "Comparing"
    builds[LOG_A].Compare(builds[LOG_B], show_ok_files)

class Collator:
    """Collect the clidiff mismatches so we can collate them
    into types and report summary information."""

    def __init__(self):
        # Key = string (comparison test), Value = {}
        #           Key = dir, Value = [(file1, file2)]
        self.records = {}

    def Add(self, test, dir, file1, file2):
        """Add a single record for "test" to our data."""
        dirs = self.records.setdefault(test, {})
        files = dirs.setdefault(dir, [])
        files.append((file1, file2))

    def AddOneOfEach(self, test, items, dir, file1, file2):
        """Add multiple related records, one "item" for each "test",
        to our data."""
        for item in items:
            self.Add(test + ": " + item, dir, file1, file2)

    def Report(self):
        """Print a report of each type of mismatch, followed by the
        files that had that mismatch."""
        tests = self.records.keys()
        tests.sort()
        for test in tests:
            print
            print test
            print "-" * len(test)
            dirs = self.records[test].keys()
            dirs.sort()
            for dir in dirs:
                print "\t", dir
                for (file1, file2) in self.records[test][dir]:
                    print "\t\t", file1
                    print "\t\t", file2
                    print "."

    def MetaReport(self):
        """Print a report that summarizes that counts [# of instances]
        of each type of mismatch."""
        tests = self.records.keys()
        tests.sort()
        records = []
        for test in tests:
            num = 0
            dirs = self.records[test].keys()
            for dir in dirs:
                num += len(self.records[test][dir])
            record = (num, test)
            records.append(record)

        # Sort by highest number of occurences
        records.sort(lambda x,y : cmp(y[0], x[0]))

        for (num, test) in records:
            if num == 1:
                print num, "time:    ", test
            else:
                print num, "times:   ", test
            print

class Build:
    """Maintains the Parser objects for each command in a build.
    The parser objects know how to parse and compare command-lines.
    Not all commands will have parser objects, since either we don't
    care about all types of commands in a build, or it would take forever
    to write plugins for every single type of command in a build."""

    def __init__(self, log_file_name, cli_plugins, map_plugin):
        self.filename = log_file_name
        self.cli_plugins = cli_plugins
        self.dirs = {}
        if map_plugin:
            self.map_cb = map_plugin.MapFilename
        else:
            self.map_cb = None

        # For each command, see if a CLI plugin can parse
        # the command-line
        self.num_unique = 0
        self.num_multiple = 0


    def ReadLogForPIDs(self, pids):
        log = LOG.LogFile(self.filename)

        # Read the log and construct the ptree
        while 1:
            try:
                rec = log.read_record()
            except EOFError:
                log.close()
                break

            if rec.pid in pids:
                pids.remove(rec.pid)
                rec.Print()
                cwd = self.NormalizeDir(rec.cwd)
                parser = self.cli_plugins.ParseRecord(rec, cwd, self.NormalizeDir)
                if parser:
                    if self.map_cb:
                        parser.AdjustFiles(self.map_cb)
                    parser.Dump()
                else:
                    print "No parser found."
                
                # Finished findind all the PIDs asked for?
                if pids:
                    print
                else:
                    return

    def ReadLog(self, pid):
        log = LOG.LogFile(self.filename)
        pid_hash = {}

        # Read the log and construct the ptree
        while 1:
            try:
                rec = log.read_record()
            except EOFError:
                log.close()
                break

            if (not pid) or (pid and rec.pid == pid):
                pid_hash[rec.pid] = rec
                self.ParseRec(rec, pid_hash)


    def ParseRec(self, rec, pid_hash):
        """Take a log record, via a call-back from walking
        the PIDTree, and try to find a parser object for the command line."""

        cwd = self.NormalizeDir(rec.cwd)
        parser = self.cli_plugins.ParseRecord(rec, cwd, self.NormalizeDir)

        if parser:
            if self.map_cb:
                parser.AdjustFiles(self.map_cb)

            parser_outputs = []
            for output_file in parser.Outputs():
                parser_outputs.append(rec.NormalizePath(output_file))

            for output_file in parser_outputs:
                (dir_, file_) = os.path.split(output_file)

                dentry_outputs = self.dirs.setdefault(dir_, {})

                if dentry_outputs.has_key(file_):
                    self.num_multiple += 1
                    print >> sys.stderr, \
                        "%s: multiple commands to create %s: %s and %s" % (self.filename, output_file,
                                dentry_outputs[file_][1], rec.pid)
                    print \
                        "%s: multiple commands to create %s: %s and %s" % (self.filename, output_file,
                                dentry_outputs[file_][1], rec.pid)

                    # Use the rec that finished last.
                    (stored_parser, stored_pid) = dentry_outputs[file_]
                    stored_rec = pid_hash[stored_pid]
                    stored_rec_end_time = stored_rec.times_end[stored_rec.REAL_TIME]
                    rec_end_time = rec.times_end[rec.REAL_TIME]

                    if rec_end_time > stored_rec_end_time:
                        dentry_outputs[file_] = (parser, rec.pid)
#                        print "Overwrote stored record with", rec
#                    else:
#                        print "Did not overwrite stored record with", rec

                else:
                    self.num_unique += 1
                    dentry_outputs[file_] = (parser, rec.pid)

    def print_2_level_list(self, items, sub_hash):
        i = 1
        all_sub_items = []
        for item in items:
            print "%8d. %s" % (i, item)
            i += 1
            j = 1
            sub_items = sub_hash[item].keys()
            sub_items.sort()
            for sub_item in sub_items:
                print "%16d. %s" % (j, sub_item)
                j += 1
                all_sub_items.append(sub_item)
            print
        return all_sub_items
   
    def Compare(self, other, show_ok_files):
        (common_dirs, excl1_dirs, excl2_dirs) = pysets.CompareLists(\
            self.dirs.keys(), other.dirs.keys())

        all_files_excl1 = []
        all_files_excl2 = []

        if excl1_dirs:
            excl1_dirs.sort()
            print "Directories (and files) in", NAME_A, "but not in", NAME_B
            files = self.print_2_level_list(excl1_dirs, self.dirs)
            all_files_excl1.extend(files)
        else:
            print "All directories in", NAME_A, "are also in", NAME_B

        print


        if excl2_dirs:
            excl2_dirs.sort()
            print "Directories (and files) in", NAME_B, "but not in", NAME_A
            files = self.print_2_level_list(excl2_dirs, other.dirs)
            all_files_excl2.extend(files)
        else:
            print "All directories in", NAME_B, "are also in", NAME_A

        # This object will collect our mismatch data for the summary report.
        collator = Collator()

        i = 1
        problem_files = []
        ok_files = []

        if common_dirs:
            print
            print "FILE BY FILE COMPARISON:"
            print "=" * 80

        for dir in common_dirs:
#            print
#            print "Directory %d = %s" % (i, dir)


            (common_outputs, excl1_outputs, excl2_outputs) = \
                pysets.CompareLists(self.dirs[dir].keys(),
                other.dirs[dir].keys())
       
#            print "%d common files." % (len(common_outputs),)
            common_outputs.sort()

            for output in common_outputs:
#                print "CHECKING", output
                parser_a, pid_a = self.dirs[dir][output]
                parser_b, pid_b = other.dirs[dir][output]

                a_file = "%s (%s PID %s)" % (output, NAME_A, pid_a)
                b_file = "%s (%s PID %s)" % (output, NAME_B, pid_b)

                # Run the comparison
                if parser_a.plugin_name == parser_b.plugin_name:
                    ok = parser_a.Compare(parser_b, dir, a_file, b_file, collator)
                else:
                    ok = parser_a.CompareValue(dir, a_file, b_file, parser_a.plugin_name,
                           parser_b.plugin_name, "CLI plugin")

                if not ok:
                    problem_files.append(os.path.join(dir, output))
                else:
                    ok_files.append(os.path.join(dir, output))

            if excl1_outputs:
                excl1_outputs.sort()
                print
                print dir
                print "Files in", NAME_A, "but not in", NAME_B
                LOG.print_enumerated_list(excl1_outputs)
                all_files_excl1.extend(excl1_outputs)

            if excl2_outputs:
                excl2_outputs.sort()
                print
                print dir
                print "Files in", NAME_B, "but not in", NAME_A
                LOG.print_enumerated_list(excl2_outputs)
                all_files_excl2.extend(excl2_outputs)

            i = i + 1

        print
        print "PROBLEMATIC FILES:"
        print "=" * 80
        problems = 0

        if all_files_excl1:
            print
            print "Files in", NAME_A, "but not in", NAME_B
            all_files_excl1.sort()
            LOG.print_enumerated_list(all_files_excl1)
            problems = 1

        if all_files_excl2:
            print
            print "Files in", NAME_B, "but not in", NAME_A
            all_files_excl2.sort()
            LOG.print_enumerated_list(all_files_excl2)
            problems = 1

        if show_ok_files and ok_files:
            print
            print "CLI's matched for these files:"
            ok_files.sort()
            LOG.print_enumerated_list(ok_files)

        if problem_files:
            print
            print "CLI differences found in build of these files:"
            problem_files.sort()
            LOG.print_enumerated_list(problem_files)
            problems = 1

        if not problems:
            print
            print "No differences found."
    
        print
        print "FILES COLLATED BY DIFFERENCE:"
        print "=" * 80
        collator.Report()

        print
        print "TYPES OF DIFFERENCES FOUND:"
        print "=" * 80
        collator.MetaReport()

        print
        print "FILE COUNTS:"
        print "=" * 80
        print "Files in", NAME_A, "but not in", NAME_B, ":", len(all_files_excl1)
        print "Files in", NAME_B, "but not in", NAME_A, ":", len(all_files_excl2)
        print "Files with no CLI difference:", len(ok_files)
        print "Files with CLI difference:", len(problem_files)

    def NormalizeDir(self, dir):
        """Given a dir, chop off the first part if the first
        part is the same as the build's initial directory."""
        
        if path_normalizer:
            return path_normalizer(dir)
        else:
            return dir

