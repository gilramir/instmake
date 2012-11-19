# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Variables and functions to aid in reading instmake logs.
"""
from __future__ import nested_scopes

import cPickle as pickle
import sys
import os
import gzip
import socket
from instmakelib import instmake_toolnames
from instmakelib import shellsyntax
from instmakelib import instmake_build

# This is imported for backwards-compatibility for
# using clearaudit data from LogRecord 5 - 11.
# With LogRecord_12, the appropriate audit plugin is loaded
# via the PluginManager.
from instmakeplugins import audit_clearaudit

VERSION_ROOT = "INSTMAKE LOG VERSION "
INSTMAKE_VERSION_1 = VERSION_ROOT + "1"
INSTMAKE_VERSION_2 = VERSION_ROOT + "2"
INSTMAKE_VERSION_3 = VERSION_ROOT + "3"
INSTMAKE_VERSION_4 = VERSION_ROOT + "4"
INSTMAKE_VERSION_5 = VERSION_ROOT + "5"
INSTMAKE_VERSION_6 = VERSION_ROOT + "6"
INSTMAKE_VERSION_7 = VERSION_ROOT + "7"
INSTMAKE_VERSION_8 = VERSION_ROOT + "8"
INSTMAKE_VERSION_9 = VERSION_ROOT + "9"
INSTMAKE_VERSION_10 = VERSION_ROOT + "10"
INSTMAKE_VERSION_11 = VERSION_ROOT + "11"
INSTMAKE_VERSION_12 = VERSION_ROOT + "12"
INSTMAKE_VERSION_13 = VERSION_ROOT + "13"
INSTMAKE_VERSION_14 = VERSION_ROOT + "14"

ORIGIN_NOT_RECORDED = "not-recorded"

CLI_PLUGIN_PREFIX = "cli"

# These are the plugins needed during reporting
PLUGIN_PREFIXES = [ instmake_toolnames.TOOLNAME_PLUGIN_PREFIX,
    CLI_PLUGIN_PREFIX, instmake_build.AUDIT_PLUGIN_PREFIX ]

# This points to a single ToolNameManager object
toolname_manager = None

# This points to a single PluginManager object
global_plugins = None

# This points to a single Printer plugin
global_printer = None

def SetPlugins(plugins):
    """Allow another module to set our 'global_plugins' variable."""
    global global_plugins
    global_plugins = plugins

    global toolname_manager
    toolname_manager = instmake_toolnames.ToolNameManager(global_plugins)

def GetPlugins():
    """Returns the 'global_plugins' variable."""
    return global_plugins

def SetPrinterPlugin(printer):
    """Allow another module to set our 'global_printer' variable."""
    global global_printer
    global_printer = printer


def WriteLatestHeader(fd, log_file_name,
        audit_plugin_name, audit_env_options, audit_cli_options):
    """Write a header to the log file. We put the version string
    first so that if someone uses "more" to view a log file,
    they easily know what it is. This function will call sys.exit()
    on failure."""
    # 0 = dump as ASCII
    header_text = pickle.dumps(INSTMAKE_VERSION_14, 0)

    header = LogHeader1(audit_plugin_name, audit_env_options, audit_cli_options)

    header_text += pickle.dumps(header)
    try:
        num_written = os.write(fd, header_text)
    except OSError, err:
        sys.exit("Failed to write to %s: %s" % (log_file_name, err))

    if num_written != len(header_text):
        sys.exit("Failed to write to %s: %s" % (log_file_name, err))


class LogRecord:
    ppid = None                 # Parent Process ID
    pid = None                  # Process ID
    cwd = None                  # Current working directory
    retval = None               # Return value of process
    times_start = None          # Start TIMES
    times_end = None            # End TIMES
    diff_times = None           # (End - Start) TIMES
    cmdline = None              # Command-line as a string
    cmdline_args = None         # Command-line as individual arguments
    make_target = None          # Make target, if using jmake --debug=e
    makefile_filename = None    # Makefile of rule, if using jmake --debug=e
    makefile_lineno = None      # Line number of rule, if using jmake --debug=e
    tool = None                 # The tool mentioned in the command-line,
                                # calculated via ToolName plugins.

    input_files = None          # Input files, if an appropriate audit
                                # plugin was used.

    output_files = None         # Output files, if an appropriate audit
                                # plugin was used.

    execed_files = None         # Executed files, if an appropriate audit
                                # plugin was used.

    audit_ok = None             # True/False: did the audit plugin succeed in
                                # auditing this command?

    env_vars = None             # Recorded environment-variables hash table.
    open_fds = None             # List of open file descriptors before the
                                # command started.
    make_vars = None            # Recorded make-variables hash table.
    make_var_origins = None     # Origins of make vars

    app_inst = None             # Application-specific instrumentation fields
                                # For instmake logs prior to 14, or for
                                # corrupt or missing app-inst data, this is
                                # None. Otherwise, it's a dictionary, which
                                # could be empty, if the app wrote an
                                # empty json dictionary.

    USER_TIME = None
    SYS_TIME = None
    REAL_TIME = None
    CPU_TIME = None

    # Does this version of the instmake log have a file header (log header)?
    HAS_LOG_HEADER = False

    # Does this version of the instmake log allow variable types of
    # audit plugins, not just clearaudit?
    HAS_VARIABLE_AUDIT_PLUGINS = False

    # Does this version of the instmake log have record classes that
    # use the LogHeader in their init() ?
    NEEDS_LOG_HEADER_IN_RECORD_INIT = False

    def TimeIndex(self, field):
        """Return the index used in the time array for a specified time,
        be it: "USER", "SYS", "REAL", or "CPU"."""
        if field == "USER":
            return self.USER_TIME
        elif field == "SYS":
            return self.SYS_TIME
        elif field == "REAL":
            return self.REAL_TIME
        elif field == "CPU":
            return self.CPU_TIME
        else:
            sys.exit("TimeIndex field '%s' not recognized." % (field,))

    def RealStartTime(self):
        """Return the real start time; this is useful for sorting records"""
        return self.times_end[self.REAL_TIME]

    def NormalizePath(self, path):
        """Given a path, if it's relative, join it with this record's CWD.
        Normalize the result, even if the path is absolute and is not joined
        with the CWD. Return the result. This method does not modify the
        record's data, even though you might think it does by its name."""
        return normalize_path(path, self.cwd)

class LogRecord_1(LogRecord):
    PARENT_PID = 0
    PID = 1
    CWD = 2
    RETVAL = 3
    START_TIMES = 4
    END_TIMES = 5
    DIFF_TIMES = 6
    ARGS = 7

    # The fields in the "times" arrays.
    SELF_USER_TIME = 0
    SELF_SYS_TIME = 1
    CHILD_USER_TIME = 2     # Normally, you use this instaed of SELF_USER_TIME
    CHILD_SYS_TIME = 3      # Normally, you use this instead of SELF_SYS_TIME
    ELAPSED_REAL_TIME = 4
    CHILD_CPU_TIME = 5

    # Short-hand time-tuple indices
    USER_TIME = CHILD_USER_TIME
    SYS_TIME = CHILD_SYS_TIME
    REAL_TIME = ELAPSED_REAL_TIME
    CPU_TIME = CHILD_CPU_TIME

    def __init__(self, array):
        self.ppid = array[self.PARENT_PID]
        self.pid = array[self.PID]
        self.cwd = array[self.CWD]
        self.retval = array[self.RETVAL]
        self.times_start = array[self.START_TIMES]
        self.times_end = array[self.END_TIMES]
        self.ConvertArgsToCmdline(array[self.ARGS])

        # Calculate CPU_TIME for diff_times
        if self.DIFF_TIMES != None:
            self.diff_times = array[self.DIFF_TIMES]
            self.diff_times += (self.diff_times[self.USER_TIME] + self.diff_times[self.SYS_TIME],)

    def ConvertArgsToCmdline(self, args):
        """Converts an array of command-line arguments to a single
        command-line string. Instmake is called 4 ways:

        1. Top-level; args are stored in an array
        2. -c, from make; the command-line is a single string.
        3 . Directly from make if make knows that the argument to $(SHELL) is
            a shell script (i.e., no -c). Args are stored in an array.
        4. -r, from jmake, to store special records. args can be stored
            as an array.
        """

        # Convert array of arguments to a single string.
        self.cmdline = ' '.join(args)

        # Then split it on whitespace, but honor quotes.
        self.cmdline_args  = shellsyntax.split_shell_cmdline(self.cmdline, 1)

    def CalculateDiffTimes(self):
        """In case the caller modifies start/end times and needs to re-calculate
        diff times."""
        # Compute the time difference.
        self.diff_times = [self.times_end[0] - self.times_start[0], # SELF USER
                    self.times_end[1] - self.times_start[1],        # SELF SYS
                    self.times_end[2] - self.times_start[2],        # CHILD USER
                    self.times_end[3] - self.times_start[3],        # CHILD SYS
                    self.times_end[4] - self.times_start[4],        # REAL
                    -1]                                             # CPU

        # Compute CPU time.
        self.diff_times[self.CPU_TIME] = self.diff_times[self.USER_TIME] + \
                                            self.diff_times[self.SYS_TIME]

    def SetTimesEnd(self, user, sys, real):
        """Set the 'times_end' attribute using the 3 new values."""
        self.times_end = (0, 0, user, sys, real)

class LogRecord_2(LogRecord_1):
    """Fields that can record jmake-exported environment variables were
    were added."""
    MAKE_TARGET = 8
    MAKEFILE_FILENAME = 9
    MAKEFILE_LINENO = 10

    def __init__(self, array):
        LogRecord_1.__init__(self, array)
        self.make_target = array[self.MAKE_TARGET]
        self.makefile_filename = array[self.MAKEFILE_FILENAME]
        self.makefile_lineno = array[self.MAKEFILE_LINENO]

class LogRecord_3(LogRecord_2):
    """The TOOL field was added."""
    # TOOL = 11 # No longer needed, as TOOL is dynamically generated,
    # even when reading a VERSION 3 log file; the new dynamically-generated
    # TOOL will override the TOOL field that was stored in the log.

    def __init__(self, array):
        LogRecord_2.__init__(self, array)
        self.tool = toolname_manager.GetTool(self.cmdline_args, self.cwd)

class LogRecord_4(LogRecord_2):
    """TOOL is no longer computed during the running of the build. Rather,
    it is computed during the reading of the log file. This allows
    for interesting ways of computing TOOL, esp. in the cases of
    interpreted languages in which you really want to know the name
    of the script and not the name of the interpretor."""
    def __init__(self, array):
        # Yes, we're a sub-class of version 2, not version 3, as
        # we're giving up the idea of a "TOOL" that was stored at build-time.
        LogRecord_2.__init__(self, array)
        self.tool = toolname_manager.GetTool(self.cmdline_args, self.cwd)

class LogRecord_5(LogRecord_4):
    """Time tuples only contain one user and one sys time."""

    # Time-tuple indices
    USER_TIME = 0
    SYS_TIME = 1
    REAL_TIME = 2
    CPU_TIME = 3

    def CalculateDiffTimes(self):
        """In case the caller modifies start/end times and needs to re-calculate
        diff times."""
        # Compute the time difference.
        self.diff_times = [self.times_end[0] - self.times_start[0], # USER
                    self.times_end[1] - self.times_start[1],        # SYS
                    self.times_end[2] - self.times_start[2],        # REAL
                    -1]                                             # CPU

        # Compute CPU time.
        self.diff_times[self.CPU_TIME] = self.diff_times[self.USER_TIME] + \
                                            self.diff_times[self.SYS_TIME]

    def SetTimesEnd(self, user, sys, real):
        """Set the 'times_end' attribute using the 3 new values."""
        self.times_end = (user, sys, real)

class LogRecord_6(LogRecord_5):
    """Add dependency information from clearaudit."""
    CLEARCASE_CATCR = 11

    def __init__(self, array):
        LogRecord_5.__init__(self, array)

        # Don't do this if we're LogRecord_12 or above.
        if not self.HAS_LOG_HEADER:
            catcr_data = array[self.CLEARCASE_CATCR]
            if catcr_data:
                audit_clearaudit.ParseData(catcr_data, self)


class LogRecord_7(LogRecord_6):
    """Add user-requested recorded environment variables."""
    RECORD_ENV_VARS = 12

    def __init__(self, array):
        LogRecord_6.__init__(self, array)
        self.env_vars = array[self.RECORD_ENV_VARS]

class LogRecord_8(LogRecord_7):
    """Add open filedescriptors."""
    OPEN_FDS = 13

    def __init__(self, array):
        LogRecord_7.__init__(self, array)
        self.open_fds = array[self.OPEN_FDS]

class LogRecord_9(LogRecord_8):
    """Add make variables."""
    RECORD_MAKE_VARS = 14

    def __init__(self, array):
        LogRecord_8.__init__(self, array)
        self.make_vars = array[self.RECORD_MAKE_VARS]
        self.make_var_origins = {}

        for key in self.make_vars.keys():
            self.make_var_origins[key] = ORIGIN_NOT_RECORDED

class LogRecord_10(LogRecord_9):
    """Remove diff-time from log; compute it at run-time."""
    DIFF_TIMES = None
    ARGS = 6
    MAKE_TARGET = 7
    MAKEFILE_FILENAME = 8
    MAKEFILE_LINENO = 9
    CLEARCASE_CATCR = 10
    RECORD_ENV_VARS = 11
    OPEN_FDS = 12
    RECORD_MAKE_VARS = 13

    def __init__(self, array):
        LogRecord_9.__init__(self, array)
        self.CalculateDiffTimes()

class LogRecord_11(LogRecord_10):
    """Values in make_vars are now tuples:
    (value, origin). If origin == "file", then the origin
    string also has the makefile filename and line number in it,
    delimited by colons."""

    def __init__(self, array):
        # Instead of running LogRecord_10.__init__, which
        # would call LogRecord_9.__init__, which would
        # create an invalid self.make_var_origins,
        # call the parts of LogRecord_10
        # and LogRecord_9 __init__ that we need
        LogRecord_8.__init__(self, array)
        self.CalculateDiffTimes()

        self.make_vars = {}
        self.make_var_origins = {}
        for varname, vartuple in array[self.RECORD_MAKE_VARS].items():
            (value, origin) = vartuple
            self.make_vars[varname] = value
            if origin:
                self.make_var_origins[varname] = origin
            else:
                self.make_var_origins[varname] = ORIGIN_NOT_RECORDED

class LogRecord_12(LogRecord_11):
    """Clearaudit information is no longer fixed field in the log.
    Instead, the audit plugin stores its data in this field. We also
    require a file header (LogHeader) so we know which
    audit plugin was used, if any."""

    HAS_LOG_HEADER = True
    HAS_VARIABLE_AUDIT_PLUGINS = True
    AUDIT_DATA = 10

    def __init__(self, array, audit_plugin):
        LogRecord_11.__init__(self, array)

        if audit_plugin:
            audit_data = array[self.AUDIT_DATA]
            audit_plugin.ParseData(audit_data, self, "")


class LogRecord_13(LogRecord_12):
    """The LogRecord init now needs log_hdr. We do this because
    audit plugins now accept audit_options during ParseData(), and
    we ge tthat from the log_hdr."""

    NEEDS_LOG_HEADER_IN_RECORD_INIT = True

    def __init__(self, array, audit_plugin, log_hdr):
        # Call LogRecord_11, and skip LogRecord_12 so we can
        # call ParseData the way we want to.
        LogRecord_11.__init__(self, array)

        if audit_plugin:
            audit_data = array[self.AUDIT_DATA]
            audit_plugin.ParseData(audit_data, self, log_hdr.audit_env_options)

class LogRecord_14(LogRecord_13):
    """Add app_inst dictionary."""

    APP_INST = 14

    def __init__(self, array, audit_plugin, log_hdr):
        # Call LogRecord_11, and skip LogRecord_12 so we can
        # call ParseData the way we want to.
        LogRecord_13.__init__(self, array, audit_plugin, log_hdr)

        self.app_inst = array[self.APP_INST]


record_version_map = {
    INSTMAKE_VERSION_1 : LogRecord_1,
    INSTMAKE_VERSION_2 : LogRecord_2,
    INSTMAKE_VERSION_3 : LogRecord_3,
    INSTMAKE_VERSION_4 : LogRecord_4,
    INSTMAKE_VERSION_5 : LogRecord_5,
    INSTMAKE_VERSION_6 : LogRecord_6,
    INSTMAKE_VERSION_7 : LogRecord_7,
    INSTMAKE_VERSION_8 : LogRecord_8,
    INSTMAKE_VERSION_9 : LogRecord_9,
    INSTMAKE_VERSION_10 : LogRecord_10,
    INSTMAKE_VERSION_11 : LogRecord_11,
    INSTMAKE_VERSION_12 : LogRecord_12,
    INSTMAKE_VERSION_13 : LogRecord_13,
    INSTMAKE_VERSION_14 : LogRecord_14,
}

# LogHeaders are versioned different from LogRecords
class LogHeader1:
    def __init__(self, audit_name, audit_env_options, audit_cli_options):
        self.audit_plugin_name = audit_name
        self.audit_env_options = audit_env_options
        self.audit_cli_options = audit_cli_options
        self.hostname = socket.gethostname()
        self.instmake_command = sys.argv

    def AuditPluginName(self):
        return self.audit_plugin_name

    def DumpInfo(self):
        # The audit env options are prepended with the audit plugin
        # name and a semicolon. Remove them for reporting purposes.

        if self.audit_plugin_name:
            options_start = len(self.audit_plugin_name) + 1
            audit_env_options = self.audit_env_options[options_start:]
        else:
            audit_env_options = ""

        print "Hostname:          ", self.hostname
        print "Audit Plugin Name: ", self.audit_plugin_name
        print "Audit Env. Options:", audit_env_options
        print "Audit CLI Options: ", self.audit_cli_options
        print "Instmake Command:  ", ' '.join(self.instmake_command)

class LogFile:
    def __init__(self, log_file_name):
        try:
            self.fh = open(log_file_name, "rb")
        except IOError, err:
            sys.exit("Cannot open %s: %s" % (log_file_name, err))

        self.orig_fh = None

        # Try to use gzip in case this is a gzipped file
        try:
            gzip_fh = gzip.GzipFile(None, None, None, self.fh)
            try:
                # See if we can read from the gzip object.
                self.record_version = self.read_allow_exceptions(gzip_fh)
                # Good; it worked. Use the gzip filehandle.
                self.orig_fh = self.fh
                self.orig_size = os.path.getsize(log_file_name)
                self.fh = gzip_fh

            except IOError:
                # Not gzipped; use original filehandle
                self.fh.seek(0)
                self.record_version = self.read()
        except:
            # Gzip module failed for some reason;
            # use original filehandle
            self.fh.seek(0)
            self.record_version = self.read()

        # Read the log header if there
        if record_version_map.has_key(self.record_version):
            self.RecordClass = record_version_map[self.record_version]
        else:
            sys.exit("The file format is not supported: %s" % \
                    (self.record_version,))

        if self.RecordClass.HAS_LOG_HEADER:
            self.hdr = self.read()
        else:
            self.hdr = None

        if global_printer:
            self.RecordClass.Print = global_printer.Print

        if self.hdr and self.hdr.AuditPluginName():
            try:
                self.audit_plugin = global_plugins.LoadPlugin( \
                        instmake_build.AUDIT_PLUGIN_PREFIX,
                        self.hdr.AuditPluginName())
            except ImportError, err:
                sys.exit("Unable to import audit-plugin '%s':\n\t%s" % \
                        (self.hdr.AuditPluginName(), err))
        else:
            self.audit_plugin = None

    def RecordVersion(self):
        return self.record_version

    def header(self):
        """Returns the LogHeader object, or None."""
        return self.hdr

    def read_allow_exceptions(self, fh):
        return pickle.load(fh)

    def read(self):
        """Read a single pickled record and unpickle it."""
        try:
            return pickle.load(self.fh)
        except ValueError, err:
            sys.exit("Could not read pickled data from log file:\n%s" \
                % (err,))
        except pickle.UnpicklingError, err:
            # Unfortunately the gzip object doesn't raise EOFError when
            # EOF is reached. So, we see if the original filehandle is
            # at the end of the file, and if so, raise EOFError.
            if self.orig_fh and self.orig_fh.tell() == self.orig_size:
                raise EOFError

            sys.exit("Could not read pickled data from log file:\n%s" \
                % (err,))

    def read_record(self):
        array = self.read()

        if self.RecordClass.NEEDS_LOG_HEADER_IN_RECORD_INIT:
            return self.RecordClass(array, self.audit_plugin, self.hdr)
        if self.RecordClass.HAS_VARIABLE_AUDIT_PLUGINS:
            return self.RecordClass(array, self.audit_plugin)
        else:
            return self.RecordClass(array)


    def close(self):
        try:
            self.fh.close()

            # The gzip object doesn't close the
            # backend filehandle, by design. We
            # do it ourselves.
            if self.orig_fh:
                self.orig_fh.close()

        except IOError:
            pass


def show_log(log_file_name):
    """Unpickle each record in the log file and print a text version
    to stdout."""

    log = LogFile(log_file_name)

    # Unpickle, a record at a time.
    while 1:
        try:
            print log.read()
        except (EOFError, IOError, KeyboardInterrupt):
            log.close()
            break

def show_log_version(log_file_name):
    """Show information about the log."""

    log = LogFile(log_file_name)
    print log.RecordVersion()

def show_log_header(log_file_name):
    """Show the log header."""

    log = LogFile(log_file_name)
    hdr = log.header()
    if hdr:
        print "Instmake Log File: ", log_file_name
        hdr.DumpInfo()
    else:
        print "This file format has no LogHeader."


SECS_IN_HOUR = 60 * 60
SECS_IN_MINUTE = 60

def hms(total_seconds):
    """Given seconds, return a string of HhMmSs"""
    (hours, remainder_minutes) = divmod(total_seconds, SECS_IN_HOUR)
    (minutes, seconds) = divmod(remainder_minutes, SECS_IN_MINUTE)

    if hours > 0:
        return "%dh%dm%.3fs" % (hours, minutes, seconds)
    elif minutes > 0:
        return "%dm%.3fs" % (minutes, seconds)
    else:
        return "%.3fs" % (seconds,)

def print_indented_list(fh, labels, data):
    """Prints a list to filehandle 'fh'. There may be some labels on the left-hand
    side, but the main data to be printed is printed on right-hand side. The data
    is indented properly so all data-items line up, and make enough room for all
    labels."""
    max_label_length = 0
    for label in labels:
        max_label_length = max(max_label_length, len(label))

    def print_line(label, datum):
        if label == None:
            label = " " * max_label_length
        else:
            len_label = len(label)
            if len_label < max_label_length:
                label += " " * (max_label_length - len_label)

        if datum == None:
            datum = ""

        print >> fh, label, datum
   
    map(print_line, labels, data)

def nxname(xname):
    """Return a non-extendend name for a ClearCase extended filename. If the
    given filename is not in extended format, it is simply returned un-changed."""
    i = xname.find("@@")
    if i == -1:
        return xname
    else:
        return xname[:i]

def print_enumerated_list(items, fh=None):
    """Print a list, enumerating each item."""
    if not fh:
        fh = sys.stdout
    i = 1
    for item in items:
        print >> fh, "%8d. %s" % (i, item)
        i += 1

def normalize_path(path, parent_path=None):
    if parent_path == None:
        return os.path.normpath(path)
    else:
        # This is Unix-only (it doesn't take into account "C:\")
        if path[0] == os.sep:
            return os.path.normpath(path)
        else:
            return os.path.normpath(os.path.join(parent_path, path))

