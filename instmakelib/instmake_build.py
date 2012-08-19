# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Routines for the "build" portion of instmake; i.e., when instmake
is running a build an recording instrumentation data.
"""
import sys
import os
import time
import cPickle as pickle
import signal
from instmakelib import jobserver

# Global constants
PID_ENV_VAR = "INSTMAKE_PID"
MAKE_SHELL_PPID_ENV_VAR = "MAKE_SHELL_PPID"
STOP_RETVAL = 101
AUDIT_PLUGIN_PREFIX = "audit"

# The path to the instmake script that was run.
SCRIPT_ENV_VAR = "INSTMAKE_SCRIPT"

# The audit plugin, if any, and its options
AUDIT_ENV_VAR = "INSTMAKE_AUDIT"

# Environment variables, if any, to record.
RECORD_ENV_ENV_VAR = "INSTMAKE_RECORD_ENV"

# Stop condition
STOP_CMD_CONTAINS_ENV_VAR = "INSTMAKE_STOP_CMD_CONTAINS"

# Binary switch settings
OPTIONS_ENV_VAR = "INSTMAKE_OPTIONS"

# Binary switch values. Each option letter must be unique, but can
# have any arbitrary value.
OPTION_OPEN_FDS = "F"

class InstmakeJobServerClient(jobserver.JobServerClient):
    env_var = "INSTMAKE_JS_FLAGS"

class InstmakeJobServer(InstmakeJobServerClient):
    def __init__(self):
        self.job_fds = os.pipe()
        self.ExportEnvVar()
        # Only one token
        self.PutToken()

    def Close(self):
        # noop, but it lets pyflakes know that the caller
        # isn't insantiating the class for no reason
        pass

def initialize_environment(argv0, record_env_vars,
    record_open_fds, stop_cmd_contains, run_instrumentation,
    audit_env_options):

    # Set the appropriate environment variables.
    if run_instrumentation:
        myself = os.path.abspath(argv0)
        os.environ[SCRIPT_ENV_VAR] = myself
        os.environ[OPTIONS_ENV_VAR] = ""
        os.environ["MAKEFLAGS"] = "SHELL=%s" % (myself,)

    # Set this environment variable to tell the sub-instmake's
    # what to do about retrieving dependency-file information.
    if audit_env_options:
        os.environ[AUDIT_ENV_VAR] = audit_env_options

    # Set the environment variable to tell instmake which
    # environment variables to record.
    if record_env_vars:
        os.environ[RECORD_ENV_ENV_VAR] = pickle.dumps(record_env_vars)

    # Tell instmake to record open file descriptors?
    if run_instrumentation and record_open_fds:
        os.environ[OPTIONS_ENV_VAR] += OPTION_OPEN_FDS

    # Stop conditions
    if stop_cmd_contains:
        os.environ[STOP_CMD_CONTAINS_ENV_VAR] = pickle.dumps(stop_cmd_contains)


def make_pid():
    """Return an instmake-style PID for this process. It's more
    than the system PID, as PIDs wrap too often on long builds."""
    # localtime[0] = YYYY
    # localtime[1] = month
    # localtime[2] = day
    # localtime[3] = hour
    # localtime[4] = minute
    # localtime[5] = second
    # localtime[6] = week day
    # localtime[7] = julian day
    # localtime[8] = daylight savings flag
    now = time.localtime()
    return "%02d%02d%02d.%d" % (now[3], now[4], now[5], os.getpid())

def find_open_fds():
    fds = []
    i = 0
    while i < 255:
        try:
            os.fstat(i)
            fds.append(i)
        except OSError:
            pass
        i += 1

    return fds


def fdwrite(fd, text):
    """Write a string to a pipe, non-atomically. Raises OSError if
    pipe is closed before writing completes."""

    num_to_write = len(text)

    while num_to_write > 0:
        num_written = os.write(fd, text)
        if num_written == 0:
            raise OSError
        else:
            num_to_write -= num_written
            if num_to_write > 0:
                text = text[num_written:]
    return


def write_record(log_file_name, ppid, pid, cretval, times1, times2,
    command_line, audit_data, makefile_filenm, makefile_lineno):
    """Write a record to the instmake log, using data passed to us, and
    other data we can find by ourself."""

    # Record open file descriptors? Do this now before we open the
    # instmake log, which would open another file descriptor.
    open_fds = None
    if os.environ.has_key(OPTIONS_ENV_VAR):
        if OPTION_OPEN_FDS in os.environ[OPTIONS_ENV_VAR]:
            open_fds = find_open_fds()

    try:
        fd = os.open(log_file_name, os.O_WRONLY|os.O_APPEND)
    except OSError, err:
        # Report the logging problem, but don't fail the build.
        print >> sys.stderr, "instmake: Failed to open %s: %s" % \
                (log_file_name, err)
        return

    # jmake variables
    make_target = os.environ.get("JMAKE_CURRENT_MAKE_TARGET", None)
    if not makefile_filenm:
        makefile_filenm = os.environ.get("JMAKE_CURRENT_MAKEFILE_FILENAME", None)
    if not makefile_lineno:
        makefile_lineno = os.environ.get("JMAKE_CURRENT_MAKEFILE_LINENO", None)
  
    # make variables exported by jmake
    make_vars = {}
    make_env_vars = filter(lambda x: x[:10] == "JMAKE_VAR_",
        os.environ.keys())

    for make_env_var in make_env_vars:
        make_var_name = make_env_var[10:]
        origin_var = "JMAKE_VOR_" + make_var_name

        if os.environ.has_key(origin_var):
            origin = os.environ[origin_var]
        else:
            origin = None

        make_vars[make_var_name] = (os.environ[make_env_var], origin)


    # Get the current working directory.
    try:
        cwd = os.getcwd()
    except OSError:
        cwd = None

    # Record the values of any environment variables that the user
    # asked us to record.
    env_var_vals = {}
    if os.environ.has_key(RECORD_ENV_ENV_VAR):
        record_env_vars = pickle.loads(os.environ[RECORD_ENV_ENV_VAR])
        for env_var in record_env_vars:
            if os.environ.has_key(env_var):
                env_var_vals[env_var] = os.environ[env_var]
            else:
                env_var_vals[env_var] = None

    # This is the record we'll save
    data = (ppid, pid, cwd, cretval, times1, times2,
            command_line, make_target, makefile_filenm,
            makefile_lineno, audit_data,
            env_var_vals, open_fds, make_vars)

    data_text = pickle.dumps(data, 1) # 1 = dump as binary

    # Write the record.
    try:
        jobclient = InstmakeJobServerClient()
    except jobserver.JobServerNotAvailable:
        # If the jobserver is missing, we don't write to the log
        # because we might corrupt the log file, esp. if the log file
        # is on NFS. But don't fail the build; just return.
        print >> sys.stderr, "instmake: can't write to log because " \
                "instmake-jobserver is not available. Not logged:", \
                data
        return

    jobclient.TakeToken()
    try:
        fdwrite(fd, data_text)
    except OSError, err:
        jobclient.PutToken()
        try:
            os.close(fd)
        except OSError:
            pass
        # Report the logging problem, but don't fail the build.
        print >> sys.stderr, "instmake: can't write to log due to", \
                err, ". Not logged:", \
                data
        return

    jobclient.PutToken()

    # Close the file-descriptor to the log file.
    try:
        os.close(fd)
    except OSError, err:
        pass


def invoke_child(log_file_name, cli_args):
    """Run a child process, record statistics, and send
    those stats to the top-most instmake process. cli_args
    are the args that should start with the command to run,
    that is, that don't start with "instmake"."""

    # Create names in the local namespace for module
    # functions that we need to call between the two
    # time-recordings. We want to minimize the amount
    # of python execution between those calls, to get
    # a better estimate of the time used in the child
    # process.
    times = os.times
    wait = os.wait
    execvp = os.execvp
    fork = os.fork
    kill = os.kill
    SIGINT = signal.SIGINT

    # Get the PPID from the environment, as
    # a previous instmake would have set it.
    ppid = os.environ.get(PID_ENV_VAR, None)

    # This instmake's PID.
    pid = make_pid()

    # Audit?
    auditor = None
    if os.environ.has_key(AUDIT_ENV_VAR):
        from instmakelib import rtimport
        i = os.environ[AUDIT_ENV_VAR].find(";")
        audit_plugin_name = os.environ[AUDIT_ENV_VAR][:i]
        audit_env_options = os.environ[AUDIT_ENV_VAR][i+1:]
        plugin_mod_name = "instmakeplugins." + AUDIT_PLUGIN_PREFIX + \
                "_" + audit_plugin_name
        audit_plugin = rtimport.rtimport(plugin_mod_name)
        auditor = audit_plugin.Auditor(audit_env_options)

    # Check for an argument other than our own name
    if len(cli_args) >= 1:
        # Makes calls us as if we are /bin/sh, so we see: ['-c', 'cmdline to run']
        if cli_args[0] == "-c":
            recorded_args = cli_args[1:]
            exec_proc_name = "/bin/sh"
            exec_proc_args = [exec_proc_name] + cli_args


        # But the first time we invoke_child() is called, make
        # didn't invoke us, so we see: ['cmdline', 'to', 'run']
        else:
            recorded_args = cli_args
            exec_proc_name = cli_args[0]
            exec_proc_args = cli_args

        # Running with an audit plugin?
        if auditor:
            exec_proc_data = \
                    auditor.ExecArgs(' '.join(recorded_args), pid)
            # Shall we modify the command-line we're going to run?
            if exec_proc_data:
                exec_proc_name, exec_proc_args = exec_proc_data

        # Change the PID info in the environment
        os.environ[PID_ENV_VAR] = pid
        os.environ[MAKE_SHELL_PPID_ENV_VAR] = str(os.getppid())

        # Record start time
        times1 = times()
        # Run the job
        cpid = fork()
        if cpid:
            try:
                cexit = wait()[1]
            except KeyboardInterrupt:
                # Send the signal to the children first, so their instmakes,
                # if any are sub-makes, can write their records.
                try:
                    kill(cpid, SIGINT)
                except OSError:
                    pass
                # make returns 2 on interrupt, so we set our cexit value to
                # 2 shifted over 16 bytes.
                cexit = 0x0200
            # Record end time
            times2 = times()
        else:
            try:
                execvp(exec_proc_name, exec_proc_args)
            except OSError, err:
                sys.exit("instmake:%s: %s" % (err, ' '.join(exec_proc_args)))
            # child process stops here
    else:
        # If given nothing to do, fake the time-recordings
        recorded_args = []
        times1 = times()
        times2 = times1
        cexit = 0

    # Convert the exit-value to a return-value by ignoring the signal
    # information.
    cretval = (cexit & 0xff00) >> 8

    if auditor:
        cretval, audit_data = auditor.CommandFinished(cexit, cretval)
    else:
        audit_data = None

    # Here are the meanings of the magic numbers, which I hard-code instead
    # of using variables for speed.
    #   CHILD_USER_TIME = 2
    #   CHILD_SYS_TIME = 3
    #   ELAPSED_REAL_TIME = 4
    new_times1 = (times1[2], times1[3], times1[4])
    new_times2 = (times2[2], times2[3], times2[4])

    # Save the data to the log.
    write_record(log_file_name, ppid, pid, cretval,
        new_times1, new_times2, recorded_args, audit_data, None, None)

    # Is there a stop condition which matches this command?
    if os.environ.has_key(STOP_CMD_CONTAINS_ENV_VAR):
        stop_cmd_contains = pickle.loads(os.environ[STOP_CMD_CONTAINS_ENV_VAR])
        for stop_cmd in stop_cmd_contains:
            for arg in recorded_args:
                if arg.find(stop_cmd) >= 0:
                    print >> sys.stderr, "*** Instmake stop condition met:", stop_cmd
                    return STOP_RETVAL

    # Return the child-process's return value.
    return cretval

def add_record(log_file_name, args):
    retval = 0
    times1 = None
    times2 = None
    cmdline = ""
    makefile_filenm = None
    makefile_lineno = None

    # Get the PPID from the environment, as
    # a previous instmake would have set it.
    ppid = os.environ.get(PID_ENV_VAR, None)

    # This instmake's PID.
    pid = make_pid()

    def usage():
        sys.exit("instmake -r [--start user sys real] [--end user sys real]\n" \
            "[--filename name] [--lineno num] [--retval val] cmd ...")

    try:
        i = 0
        len_args = len(args)
        while i < len_args:
            arg = args[i]
            if arg == "--start":
                times1 = (float(args[i+1]), float(args[i+2]), float(args[i+3]))
                i += 3
            elif arg == "--end":
                times2 = (float(args[i+1]), float(args[i+2]), float(args[i+3]))
                i += 3
            elif arg == "--retval":
                retval = int(args[i+1])
                i += 1
            elif arg == "--filenm":
                makefile_filenm = args[i+1]
                i += 1
            elif arg == "--lineno":
                makefile_lineno = int(args[i+1])
                i += 1
            else:
                cmdline = args[i:]
                break

            i += 1

    except IndexError:
        usage()

    except ValueError:
        usage()

    if times1 == None:
        sys_times1 = os.times()
        # Here are the meanings of the magic numbers, which I hard-code instead
        # of using variables for speed.
        #   CHILD_USER_TIME = 2
        #   CHILD_SYS_TIME = 3
        #   ELAPSED_REAL_TIME = 4
        times1 = (sys_times1[2], sys_times1[3], sys_times1[4])

    if times2 == None:
        times2 = times1

    write_record(log_file_name, ppid, pid, retval, times1, times2, cmdline,
        None, makefile_filenm, makefile_lineno)

    # Return the child-process's return value.
    sys.exit(retval)
