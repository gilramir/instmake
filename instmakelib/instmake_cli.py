# Copyright (c) 2010 by Cisco Systems, Inc.
from __future__ import nested_scopes

import sys
import getopt
from instmakelib import imlib
from instmakelib import instmake_log
from instmakelib import instmake_build
import os


# Major modes
NO_MODE = -1
STATS = "report"
SHOW_LOG_VERSION = "show-log-version"
SHOW_TEXT = "text"
SHOW_CSV = "csv"
BUILD = "build"
HELP = "help"
SHOW_LOG_HEADER = "show-log-header"

# Global constants
REPORT_PLUGIN_PREFIX = "report"
PRINT_PLUGIN_PREFIX = "print"
FILEMAP_PLUGIN_PREFIX = "filemap"
DEFAULT_PRINT_PLUGIN = "default"
HELP_OPTION = "--help"

PLUGIN_PREFIXES = [
        instmake_build.AUDIT_PLUGIN_PREFIX,
        REPORT_PLUGIN_PREFIX,
        PRINT_PLUGIN_PREFIX,
        FILEMAP_PLUGIN_PREFIX
]

def start_plugin_manager(plugin_dirs):
    return imlib.start_plugin_manager(plugin_dirs,
            PLUGIN_PREFIXES)

def print_plugin_descriptions(plugins, prefix):
    names = plugins.PluginNames(prefix)
    names.sort()
    descriptions = []

    if not names:
        print "(None)"
        return

    for name in names:
        try:
            mod = plugins.LoadPlugin(prefix, name)
        except ImportError, err:
            sys.exit("Unable to import %s-plugin '%s':\n\t%s" % (prefix, name, err))

        if mod and hasattr(mod, "description"):
            descriptions.append(mod.description)
        else:
            descriptions.append("No description.")

    instmake_log.print_indented_list(sys.stdout, names, descriptions)

def usage(plugin_dirs):

    print "instmake usage:"
    print "   BUILD:"
    print "\tinstmake [-L log_file|--vws=prefix|--logs=prefix] [--force]"
    print "\t\t[--noinst] [-a audit-plugin[,options]]"
    print "\t\t[-o make_output_file] [-e env-var] [--fd]"
    print "\t\t[--stop-cmd-contains text]"
    print "\t\tmake ..."
    print
    print "   REPORT:"
    print "\tinstmake [-P plugin_dir] [-L log_file] [-L log_file] [-d|--default]"
    print "\t\t[--vws=prefix] [--logs=prefix] [-p|--print print-plugin]"
    print" \t\t[-s|--stats report-name] [%s] [options]" %  (HELP_OPTION,)
    print
    print "   MISCELLANEOUS:"
    print "\tinstmake [-L log_file|--vws=prefix|--logs=prefix] [-t|--text]"
    print "\tinstmake [-L log_file|--vws=prefix|--logs=prefix] [-c|--csv]"
    print "\tinstmake [-L log_file|--vws=prefix|--logs=prefix] [--log-version]"
    print "\tinstmake [-L log_file|--vws=prefix|--logs=prefix] [--log-header]"
    print "\tinstmake [-P plugin_dir] [-h|--help]"
    print
    print " The following options can be repeated as many times as necessary:"
    print "\t[-P plugin_dir]"
    print "\t[-e env-var]"
    print "\t[--stop-cmd-contains text]"

    plugins = start_plugin_manager(plugin_dirs)


    print 
    print "Print Plugins:"
    print "=============="
    print_plugin_descriptions(plugins, PRINT_PLUGIN_PREFIX)

    print 
    print "Audit Plugins: (for plugin-specific options, use:"
    print "==============      instmake -a report-name %s)" % (HELP_OPTION,)
    print_plugin_descriptions(plugins, instmake_build.AUDIT_PLUGIN_PREFIX)

    print 
    print "Reports Plugins: (for plugin-specific options, use:"
    print "================      instmake -s report-name %s)" % (HELP_OPTION,)
    print_plugin_descriptions(plugins, REPORT_PLUGIN_PREFIX)


    sys.exit(1)

def redirect_make_output(output_file):
    # Open the output file
    file_mode = 0644
    try:
        output_fd = os.open(output_file, os.O_CREAT|os.O_TRUNC|os.O_WRONLY,
            file_mode)
    except OSError, err:
        sys.exit("Could not open %s for writing: %s" % (output_file, err))

    # Duplicate current stdout to the output file
    os.dup2(output_fd, 1)

    # Duplicate current stderr to the output file
    os.dup2(output_fd, 2)

    # We can close the orig output_fd
    try:
        os.close(output_fd)
    except OSError, err:
        print >> sys.stderr, "Error closing %s: %s" % (output_file, err)

def LogFiles(log_prefix):
    """Determines the filenames for the instmake log and the make output log
    by using an arbitrary prefix.  Returns a tuple of the two filenames
    (instmake_log, make_log)."""
    imlog = log_prefix + ".imlog"
    mklog = log_prefix + ".make.out"
    return (imlog, mklog)

def VWSLogFiles(log_prefix):
    """Determines the filenames for the instmake log and the make output log
    by using the ClearCase view-working-storage directory, plus a prefix that
    the user provides. Returns a tuple of the two filenames (instmake_log,
    make_log)."""
    from instmakelib import ct
    try:
        view = ct.View()
    except ct.NotAView:
        sys.exit("Cannot run cleartool. Is this a ClearCase view?")

    vws_parent_dir = view.VWS_ParentDir()
    view.Close()

    return LogFiles(os.path.join(vws_parent_dir, log_prefix))


def start_plugins_for_reading(plugin_dirs):
    plugins = start_plugin_manager(plugin_dirs)
    instmake_log.SetPlugins(plugins)
    return plugins

def run_report(report_name, printer_name, log_file_names, plugin_dirs,
        report_args, assumed_default_logfile):
    """Run a report, given a few values."""
    
    plugins = start_plugins_for_reading(plugin_dirs)

    # Load the report plugin
    try:
        mod = plugins.LoadPlugin(REPORT_PLUGIN_PREFIX, report_name)
    except ImportError, err:
        sys.exit("Unable to import report '%s':\n\t%s" % (report_name, err))

    if not mod:
        sys.exit("No such report: %s" % (report_name,))

    if HELP_OPTION in report_args:
        print "instmake '%s' report-plugin usage:" % (report_name,)
        print
        mod.usage()
        sys.exit(0)

    # Load the print plugin
    try:
        printer = plugins.LoadPlugin(PRINT_PLUGIN_PREFIX, printer_name)
    except ImportError, err:
        sys.exit("Unable to import print-plugin '%s':\n\t%s" % (printer_name, err))

    # Let the print plugin print a header; in the future, the pring plugin
    # should change to be a class
    if printer:
        printer.PrintHeader()
    else:
        sys.exit("No such print-plugin: %s" % (printer_name,))

    instmake_log.SetPrinterPlugin(printer)

    # Some reports don't like for us to assume a default log file.
    if assumed_default_logfile:
        if hasattr(mod, "ASSUME_DEFAULT_LOGFILE"):
            if not mod.ASSUME_DEFAULT_LOGFILE:
                assert len(log_file_names) == 1
                assert log_file_names[0] == \
                        os.path.expanduser(imlib.DEFAULT_LOG_FILE)
                log_file_names = []

    # Check that the log files exist.
    for file_name in log_file_names:
        if not os.path.exists(file_name):
            sys.exit("%s does not exist." % (file_name,))

        if not os.path.isfile(file_name):
            sys.exit("%s is not a file." % (file_name,))

    # Run the report
    try:
        mod.report(log_file_names, report_args)
    except KeyboardInterrupt:
        sys.exit("Instmake report interrupted by user.")

    # Let the print plugin print a header
    printer.PrintFooter()

def start_top(log_file_env_var, config, site_dir):
    """Starting the top-most instmake. Decide which major
    function to run: begin a new database, append to a database,
    or run statistics."""

    log_file_name = None
    report_name = None
    log_file_names = []
    make_output_file = None
    if site_dir:
        plugin_dirs = [site_dir]
    else:
        plugin_dirs = []
    force_logfile_overwrite = 0
    mode = NO_MODE
    printer_name = DEFAULT_PRINT_PLUGIN
    record_env_vars = []
    record_open_fds = 0
    stop_cmd_contains = []
    run_instrumentation = 1
    audit_name = None
    audit_plugin = None
    audit_env_options = ""
    audit_cli_options = []
    assumed_default_logfile = 0

    ################################
    # Parse the command-line options
    optstring = "a:L:P:o:stdchp:e:"
    longopts = ["text", "stats", "default", "log-version", "log-header",
            "csv", "help",
        "force", "print", "vws=", "fd",
        "stop-cmd-contains=", "noinst", "logs="]

    imlib.SetConfig(config)

    try:
        opts, args = getopt.getopt(sys.argv[1:], optstring, longopts)
    except getopt.GetoptError:
        usage(plugin_dirs)

    for opt, arg in opts:
        if opt == "-L":
            log_file_name = arg
            log_file_names.append(arg)

        elif opt == "-P":
            plugin_dirs.append(arg)

        elif opt == "-o":
            make_output_file = arg

        elif opt == "--vws":
            (log_file_name, make_output_file) = VWSLogFiles(arg)
            log_file_names.append(log_file_name)

        elif opt == "--logs":
            (log_file_name, make_output_file) = LogFiles(arg)
            log_file_names.append(log_file_name)

        elif opt == "-e":
            record_env_vars.append(arg)

        elif opt == "-d" or opt == "--default":
            log_file_name = os.path.expanduser(imlib.DEFAULT_LOG_FILE)
            log_file_names.append(log_file_name)

        elif opt == "-t" or opt == "--text":
            if mode != NO_MODE:
                usage(plugin_dirs)
            mode = SHOW_TEXT

        elif opt == "-c" or opt == "--csv":
            if mode != NO_MODE:
                usage(plugin_dirs)
            mode = SHOW_CSV

        elif opt == "--log-version":
            if mode != NO_MODE:
                usage(plugin_dirs)
            mode = SHOW_LOG_VERSION

        elif opt == "--log-header":
            if mode != NO_MODE:
                usage(plugin_dirs)
            mode = SHOW_LOG_HEADER

        elif opt == "-s" or opt == "--stats":
            if mode != NO_MODE:
                usage(plugin_dirs)
            mode = STATS

        elif opt == "--force":
            force_logfile_overwrite = 1

        elif opt == "--fd":
            record_open_fds = 1

        elif opt == "--stop-cmd-contains":
            stop_cmd_contains.append(arg)

        elif opt == "--noinst":
            run_instrumentation = 0

        elif opt == "-a":
            if audit_env_options:
                sys.exit("-a can only be specified once.")

            plugins = start_plugin_manager(plugin_dirs)
            if arg.find(","):
                split_args = arg.split(",")
                audit_name = split_args[0]
                audit_cli_options = split_args[1:]
            else:
                audit_name = arg
                audit_cli_options = []
            try:
                mod = plugins.LoadPlugin(instmake_build.AUDIT_PLUGIN_PREFIX,
                        audit_name)
            except ImportError, err:
                sys.exit("Unable to import plugin '%s':\n\t%s" % \
                        (audit_name, err))

            audit_env_options = mod.CheckCLI(audit_cli_options)
            audit_env_options = audit_name + ";" + audit_env_options
            audit_plugin = mod


        elif opt == "-p" or opt == "--print":
            printer_name = arg

        elif opt == "-h" or opt == "--help":
            mode = HELP

        else:
            sys.exit("Unhandled CLI option:" + opt)


    #############
    # Mode checks

    # If there was no specific mode selected, then we're building.
    if mode == NO_MODE:
        mode = BUILD

    # General help, or audit-plugin help?
    # (Report-plugin help is handled later)
    if mode == HELP:
        if audit_plugin:
            audit_plugin.usage()
            sys.exit(1)
        else:
            usage(plugin_dirs)

    # Default log file
    if not log_file_name:
        log_file_name = os.path.expanduser(imlib.DEFAULT_LOG_FILE)
        log_file_names.append(log_file_name)
        assumed_default_logfile = 1

    # Text mode can't have any additional arguments
    if (mode == SHOW_TEXT) and args:
        usage(plugin_dirs)

    # CSV mode can't have any additional arguments
    if (mode == SHOW_CSV) and args:
        usage(plugin_dirs)

    # Log-version mode can't have any additional arguments
    if (mode == SHOW_LOG_VERSION) and args:
        usage(plugin_dirs)

    # Log-header mode can't have any additional arguments
    if (mode == SHOW_LOG_HEADER) and args:
        usage(plugin_dirs)

    # If stat mode, grab the report name
    if mode == STATS:
        if len(args) == 0:
            usage(plugin_dirs)
        report_name = args[0]
        report_args = args[1:]

    # Print plugin can only be chosen in stat mode
    if printer_name != DEFAULT_PRINT_PLUGIN and mode != STATS:
        sys.exit("Print plugin can only be used with --stats")

    # Audit plugin can only be chosen in build mode
    # (help mode was already handled above)
    if audit_plugin and mode != BUILD:
        sys.exit("Audit plugin can only be used when building")

    # If we're supposed to read the log file(s), check
    # that they exist. But don't do this for report plugins, as
    # that check will come later.
    if mode != BUILD and mode != STATS:
        for file_name in log_file_names:
            if not os.path.exists(file_name):
                sys.exit("%s does not exist." % (file_name,))

            if not os.path.isfile(file_name):
                sys.exit("%s is not a file." % (file_name,))

    #########################
    # Finally, run something.
    if mode == STATS:
        # Instmake recoreds are plain Python data types (lists, tuples,
        # dictionaries, strings), but the LogHeader_1 that was added
        # is a Python object, for which a class is neeeded. This was a
        # mistake!
        # In pre-open-source instmake logs, unpickle() will try to
        # import 'instmake_log', but that won't work because in open-source
        # instmake, 'instmake_log' has been moved to the instmakelib directory.
        # To allow the open-source version of instmake to read instmake logs
        # from before it was released to open source, we add the instmakelib
        # directory to sys.path.
        instmake_lib_path = os.path.dirname(__file__)
        sys.path.append(instmake_lib_path)

        run_report(report_name, printer_name, log_file_names, plugin_dirs,
                report_args, assumed_default_logfile)
        return mode, None

    elif mode == SHOW_TEXT:
        if len(log_file_names) != 1:
            sys.exit("--text uses only one log file.")
        # Just convert the pickle file to text
        start_plugins_for_reading(plugin_dirs)
        instmake_log.show_log(log_file_name)
        return mode, None

    elif mode == SHOW_CSV:
        if len(log_file_names) != 1:
            sys.exit("--csv uses only one log file.")

        # Print the CSV header; unfortunately, if run_report fails, the user
        # will have this header printed to STDOUT anyway.
        print "PID,",
        print "TOOL,",
        print "CWD,",
        print "RETVAL,",
        print "USER_SECS,",
        print "SYS_SECS,",
        print "REAL_SECS,",
        print "TARGET,",
        print "MAKEFILE,",
        print "LINE,",
        print "START_TIME,",
        print "END_TIME"

        # Run the 'dump' report with the 'csv' printer
        run_report('dump', 'csv', log_file_names, plugin_dirs, [],
            assumed_default_logfile)
        return mode, None

    elif mode == SHOW_LOG_VERSION:
        if len(log_file_names) != 1:
            sys.exit("--log-version uses only one log file.")
        # Read the log, and report the version
        start_plugins_for_reading(plugin_dirs)
        instmake_log.show_log_version(log_file_name)
        return mode, None

    elif mode == SHOW_LOG_HEADER:
        if len(log_file_names) != 1:
            sys.exit("--log-header uses only one log file.")
        # Read the log, and report the header
        start_plugins_for_reading(plugin_dirs)
        instmake_log.show_log_header(log_file_name)
        return mode, None

    elif mode == BUILD:
        # Start a build

        # Ensure 1 log_file_name, and that it's absolute. A
        # sub-make can chdir, so we better not have a relative log file name.
        if len(log_file_names) != 1:
            sys.exit("instmake can write to only one log file.")

        if not os.path.isabs(log_file_name):
            log_file_name = os.path.abspath(log_file_name)

        # Set up the environment variables.
        os.environ[log_file_env_var] = log_file_name
        instmake_build.initialize_environment(sys.argv[0],
            record_env_vars, record_open_fds,
            stop_cmd_contains, run_instrumentation, audit_env_options)

        # We've got to wrap *something*.
        if len(args) == 0:
            usage(plugin_dirs)

        # Don't overwrite an existing log file unless asked to do so.
        if not force_logfile_overwrite:
            if os.path.exists(log_file_name):
                sys.exit("%s already exists.\nRemove or use --force option." \
                    % (log_file_name,))

        # Create a new log file.
        file_mode = 0644
        try:
            fd = os.open(log_file_name, os.O_CREAT|os.O_TRUNC|os.O_WRONLY,
                file_mode)
        except OSError, err:
            sys.exit("Failed to open %s: %s" % (log_file_name, err))

        # Write a header to the log file.
        instmake_log.WriteLatestHeader(fd, log_file_name,
            audit_name, audit_env_options, audit_cli_options)

        # Close the file.
        try:
            os.close(fd)
        except OSError, err:
            sys.exit("Failed to close %s: %s" % (log_file_name, err))

        # Redirect output
        if make_output_file:
            redirect_make_output(make_output_file)

        # Run the job
        jobserver = instmake_build.InstmakeJobServer()
        rc = instmake_build.invoke_child(log_file_name, args)
        jobserver.Close()
        return mode, rc

    else:
        sys.exit("Unexpected mode: %s" % (mode,))
