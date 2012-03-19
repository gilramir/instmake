"""
Record strace output each commands
"""

import os
import re
import sys
import subprocess
import tempfile

from instmakelib import straceparse

description = "Record syscalls via strace"

# CLI options
OPT_STRACE = "strace"
OPT_EXTERNAL = "ext-logs"
OPT_LEAVE_COMMANDS = "leave-cmds"
OPT_WORK_DIR = "work-dir"

# Leave or remove the shell scripts
LEAVE = "L"
REMOVE = "R"

# Should the strace logs be external or internal to the instmake log
EXTERNAL_LOGS = "X"
INTERNAL_LOGS = "I"

# strace_prog = 'strace'
#STRACE_PROG = "strace"
STRACE_PROG = "/ws/rathreya-sjc/lbt-prototype/strace/bin/strace"

# Environment variables
STRACE_PROG_ENV_VAR = "INSTMAKE_STRACE_PROG"
LOG_DIR_ENV_VAR = "INSTMAKE_STRACE_LOG_DIR"


# it should be only "make", "jmake" for the actual plugin
MAKE_CMDS      = [ "make", "jmake",  "iosmake", "cbs" ] 
NO_STRACE_CMDS = [ "mib-sys-symlinks" ]


def usage():
    print "strace:", description

    print "  %s=STRACE : use STRACE instead of strace found in PATH" % \
            (OPT_STRACE,)
    print "                  (or use env var INSTMAKE_STRACE_PROG)"

    print "       %s : keep strace log files external from instmake log" % \
            (OPT_EXTERNAL,)

    print "     %s : leave the temporary shell scripts on disk" % \
            (OPT_LEAVE_COMMANDS,)

    print "   %s=DIR : use DIR for temporary shell scripts and strace logs" % \
            (OPT_WORK_DIR,)
    print "                  (or use INSTMAKE_STRACE_LOG_DIR)"


def CheckCLI(options):
    LEAVE_CMDS = REMOVE
    EXTERNAL = INTERNAL_LOGS
    STRACE = os.environ.get(STRACE_PROG_ENV_VAR, STRACE_PROG)
    WORK_DIR = os.environ.get(LOG_DIR_ENV_VAR, tempfile.gettempdir())

    # Parse the audit options
    for option in options:
        # Check the boolean options
        if option.find("=") == -1:
            if option == OPT_LEAVE_COMMANDS:
                LEAVE_CMDS = LEAVE
            elif option == OPT_EXTERNAL:
                EXTERNAL = EXTERNAL_LOGS
            else:
                sys.exit("Unrecognized strace audit option '%s'" % (option,))

        # Check the options with values
        else:
            try:
                lhs, rhs = option.split("=")
            except ValueError, e:
                # Too many ='s
                sys.exit("Error with option %s: %s" % (option, e))
            if lhs == OPT_STRACE:
                STRACE = rhs
            elif lhs == OPT_WORK_DIR:
                WORK_DIR = rhs
            else:
                sys.exit("Unrecognized strace audit option '%s'" % (option,))

    # Sanity check
    if not os.path.isdir(WORK_DIR):
        try:
            os.makedirs(WORK_DIR)
        except OSError, e:
            sys.exit("Unable to mkdir -p %s : %s" % (WORK_DIR, e))

    # See if we can execute strace
    cmdv = [STRACE, "ls"]
    try:
        # No need to grab the output; we are only checking that
        # execution of cmdv does not fail.
        subprocess.check_output(cmdv, stderr=subprocess.STDOUT)
    except:
        sys.exit("Unable to execute '%s'" % (' '.join(cmdv)))

    audit_options = "|".join([LEAVE_CMDS, EXTERNAL, STRACE, WORK_DIR])
    return audit_options

class Auditor:
    def __init__(self, audit_options):
        (self.leave_temp, self.ext_logs,
                self.strace, self.temp_dir) = audit_options.split("|")
        self.cmd_file       = None
        self.strace_op_file = None

    def ExecArgs(self, cmdline, instmake_pid):

        # we are saving the command in a file and making the strace to execute
        # the cmd file itself, because the following will effect the strace run
        # 1) variable declaration cannot be run under strace like,
        #      strace this_var=foo
        # 2) the shell redirections output cannot be captured other wise
        #      strace -o /tmp/strace.out 'my_prog > /tmp/1'
        #      does not capture /tmp/1 because it is written by shell not the
        #      process spawned by shell
        # 3) some commands cannot be executed under strace ( if the command is
        # not a binary and does not start with #!, shell can execute them by
        # simply running under 'sh' program. )
        # sow we need to create a cmd file for strace.

        if ok_to_run_strace(cmdline):
            self.cmd_file = self.create_cmd_file(cmdline, instmake_pid)
            self.strace_op_file = os.path.join(self.temp_dir,
                    "strace.%s" % instmake_pid)

            # touch the strace file so that we know for this command we are
            # running under strace.
            os.system("touch %s" % self.strace_op_file)

            exec_proc = self.strace
            exec_args = [self.strace, "-f", "-o", self.strace_op_file,
                    "sh", self.cmd_file]

            return exec_proc, exec_args

        else:
            # Don't change the command-line
            return None


    def CommandFinished(self, cexit, cretval):
        """Returns a tuple: (retval of command, text result of strace)"""

        strace_output = None

        if self.cmd_file:
            # Either leave or remove the cmd file
            if self.leave_temp == REMOVE:
                try:
                    os.unlink(self.cmd_file)
                except OSError:
                    pass

            # If user has requested external logs, we store
            # the filename
            if self.ext_logs == EXTERNAL_LOGS:
                strace_output = (self.cmd_file, self.strace_op_file)

            # Otherwise we put the contents of the strace log into
            # the instmake log
            elif self.ext_logs == INTERNAL_LOGS:
                try:
                    fh = open(self.strace_op_file)
                    strace_output = (self.cmd_file, fh.read())
                except IOError:
                    return (cretval, None)

                try:
                    fh.close()
                except IOError:
                    pass

            if self.leave_temp == REMOVE:
                try:
                    os.unlink(self.cmd_file)
                except OSError:
                    pass

                if self.ext_logs == INTERNAL_LOGS:
                    try:
                        os.unlink(self.strace_op_file)
                    except OSError:
                        pass
       
        return cretval, strace_output


    def create_cmd_file(self, cmdline, instmake_pid):
        """ creates a command file temp_dir/cmds.<instmake_pid> """

        cmd_file = os.path.join(self.temp_dir, "cmd.%s" % instmake_pid)

        try:
            fw = open(cmd_file, "w")

            # we write cd %s because we want the strace output to capture curr
            # dir using chdir 

            fw.write("cd %s\n" % os.getcwd())
            fw.write(cmdline + "\n");
            fw.close()
        except IOError:
            sys.exit("%s: could not write to the command file" % cmd_file)

        return cmd_file


def ParseData(audit_data, log_record, audit_env_options) :
    """Read the strace data."""
    if not audit_data:
#        print >> sys.stderr, "No audit data"
        return

    (leave_temp, ext_logs,
            strace, temp_dir) = audit_env_options.split("|")

    (cmd_file, strace_op_data) = audit_data
#    print >> sys.stderr, "ext_logs:", ext_logs, "cmd_file:", cmd_file, "strace_op_data:", strace_op_data
    if ext_logs == EXTERNAL_LOGS:
        strace_data = straceparse.StraceFile(strace_op_data)
    else:
        strace_data = straceparse.StraceOutput(strace_op_data)

    # Ignore the command-file
    strace_data.remove_read(cmd_file)
    log_record.input_files = strace_data.get_files_read()
    log_record.output_files = strace_data.get_files_written()



def ok_to_run_strace(cmdline):
    if  is_empty_cmd(cmdline) or \
        is_make_cmd(cmdline) or \
        is_nostrace_cmd(cmdline):
        return False

    return True


def is_make_cmd(cmdline):
    # There can be more than one tools used in each command line. 
    tool_names = get_tool_names(cmdline)

    if None in tool_names:
#        print >> sys.stderr, cmdline, " COULD NOT DETERMINE TOOLNAME"
        return False

    # check if any tool matches the MAKE_CMDS.
    for tool_name in tool_names:
        for make_cmd in MAKE_CMDS:
            if tool_name.startswith(make_cmd):
                return True

    return False

        
def is_nostrace_cmd(cmdline):
    for tool in get_tool_names(cmdline):
        if tool in NO_STRACE_CMDS:
            return True
    return False

EMPTY_CMD_REGEX  = re.compile(r'^\s*$')
def is_empty_cmd(cmdline):
    if cmdline.startswith('#') or \
        EMPTY_CMD_REGEX.match(cmdline):
        return True
    else:
        return False




# FIXME: use tool manager
def get_tool_names(cmdline):
    """ returns all the tools that are used as part of a shell command line """
    tool_names = []
    for cmd in re.split(';|\||\&|\(', cmdline):
        if is_empty_cmd(cmd):
            continue
        tool_names.append(get_tool_name_cmd(cmd))

    return tool_names

def get_tool_name_cmd(cmd):
    """ returns the tool name for a given a sub-cmd, a shell command that does
    not contain any other subcommands it in """
    args = cmd.split()
    arg0_basename = os.path.basename(args[0])

    if arg0_basename == 'env':
        i = 0
        for arg in args[1:]:
            i = i + 1
            if arg.startswith('-') or ('=' in arg):
                continue
            return get_tool_name_cmd(' '.join(args[i:]))

    if arg0_basename == 'time':
        i = 0
        for arg in args[1:]:
            i = i + 1
            if arg.startswith('-'):
                continue
            return get_tool_name_cmd(' '.join(args[i:]))

    if arg0_basename == 'flock':
        lock_file_arg = None
        i = 0
        for arg in args[1:]:
            i = i + 1
            if arg.startswith('-'):
                continue
            elif lock_file_arg is None:
                lock_file_arg = arg
            else:
                return get_tool_name_cmd(' '.join(args[i:]))

    return arg0_basename


