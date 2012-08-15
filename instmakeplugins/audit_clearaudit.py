"""
Use clearaudit to record file I/O when building in a ClearCase view.
"""

import os
import re
import sys

description = "Record file I/O in ClearCase"

CLEARAUDIT_SHELL_ENV_VAR = "CLEARAUDIT_SHELL"

NORMAL = "N"
FULL = "F"

def usage():
    print "clearaudit:", description
    print "    full : slower build, but captures file I/O on failed " \
            "commands, too"
    print "leave-do : leave the Derived Objects in the view"

def run_command(command):
    """Runs a command and returns the output as an array of strings, each string
    being a single line of output. Returns None if the command failed for any
    any reason."""
    try:
        pipe = os.popen(command)
        data = pipe.readlines()
        error = pipe.close()
        if error:
            return None

    except OSError:
        return None

    return data


def CheckCLI(options):
    # clearaudit will look at CLEARAUDIT_SHELL before it looks at SHELL, which
    # is good because 'make' will set SHELL because instmake is setting SHELL
    # via MAKEFLAGS; we do not want clearaudit to use SHELL, and thus
    # recursively call instmake. 
    if os.environ.has_key(CLEARAUDIT_SHELL_ENV_VAR):
        print >> sys.stderr, "instmake -a=%s needs to set " \
            "the %s environment variable." % \
            (plugin_name, CLEARAUDIT_SHELL_ENV_VAR)
        print >> sys.stderr, "\tYou already have it set; please unset " \
            "it and run instmake again."
        sys.exit(1)

    # We should not tell clearaudit to use $SHELL to run commands, as make
    # uses /bin/sh, so discrepenancies could occur between a non-instmake make,
    # or a instmake, non-clearaudit make, and an instmake/clearaudit make.
    # This is because 1) csh is totally different and 2) bash has built-ins
    # that /bin/sh doesn't.
    os.environ[CLEARAUDIT_SHELL_ENV_VAR] = "/bin/sh"

    normal_or_full = NORMAL
    leave_DO = "F"

    for option in options:
        if option == "full":
            normal_or_full = FULL
        elif option == "leave-do":
            leave_DO = "T"
        else:
            sys.exit("clearaudit plugin: unexpected option: " + option)

    env_options = normal_or_full + leave_DO
    return env_options

# Are we running an flock command? If so, and we're running clearaudit,
# we'll want to re-arrange the flock and clearaudit so that the
# clearaudit runs under the flock, not the flock under the clearaudit.
re_flock_cmd = re.compile(r"^(?P<flock>(/router/bin/)?flock\s+-\w{1,2}(\s+-\w{1,2})?\s+\S+)\s+(?P<command>.*)$")

# The command succeeded but the audit failed
AUDIT_FAILED = -1

class Auditor:
    def __init__(self, audit_options):
        self.full = 0
        self.leave_DO = 0

        if audit_options[0] == "F":
            self.full = 1

        if audit_options[1] == "T":
            self.leave_DO = 1

        self.derived_object = None

    def ExecArgs(self, cmdline, instmake_pid):
        if self.full:
            return self.mod_cmdline_for_clearaudit_full(cmdline, instmake_pid)
        else:
            return self.mod_cmdline_for_clearaudit(cmdline, instmake_pid)

    def mod_cmdline_for_clearaudit(self, cmdline, pid):
        """Given a command-line, modify it for running under clearaudit."""

        # We create a "throw-away" derived-object.
        self.derived_object = os.path.abspath("instmake.clearaudit.DO." + pid)

        # Running an flock?
        m = re_flock_cmd.search(cmdline)
        if m:
            flock_cmdline = m.group("flock")
            command_cmdline = m.group("command")

            exec_proc_name = flock_cmdline.split()[0]
            exec_proc_args = flock_cmdline.split()
            exec_proc_args.extend(["clearaudit", "-c", ":>" + \
                    self.derived_object + "; " + command_cmdline])

        else:
            exec_proc_name = "clearaudit"
            exec_proc_args = [exec_proc_name, '-c', ":>" + \
                    self.derived_object + "; " + cmdline]

        return exec_proc_name, exec_proc_args

    def mod_cmdline_for_clearaudit_full(self, cmdline, pid):
        """Given a command-line, modify it for running under clearaudit-full."""

        from Text import shellsyntax

        cmdline = shellsyntax.remove_trailing_comment(cmdline)

        echo = "echo $? >"

        # We create a "throw-away" derived-object. It serves 2 purposes:
        # 1. It's configuration record contains the files read and written
        # 2. The contents are the exit status of the command.
        self.derived_object = os.path.abspath("instmake.clearaudit.DO." + pid)

        # Running an flock?
        m = re_flock_cmd.search(cmdline)
        if m:
            flock_cmdline = m.group("flock")
            command_cmdline = m.group("command")

            exec_proc_name = flock_cmdline.split()[0]
            exec_proc_args = flock_cmdline.split()
            exec_proc_args.extend(["clearaudit", "-c",
                "( " + command_cmdline + " );" + echo + self.derived_object])
        else:
            # Run the command in a "sub-shell" (in parens) so that exits
            # are handled # properly as far as the command is concerned.
            # Spaces are needed after the first paren and before the last
            # paren to guard against commands that already use parens
            # resulting in double-parens, like "((cd .. ; ls))", which
            # is bad syntax.
            # We grab the exit value and save it to the
            # DO file for later processing.
            exec_proc_name = "clearaudit"
            exec_proc_args = [exec_proc_name, '-c', \
                    "( " + cmdline + " );" + echo + self.derived_object]

        return exec_proc_name, exec_proc_args


    def CommandFinished(self, cexit, cretval):
        """Returns a tuple: (retval of command, (catcr text, DO name))"""
        # Get the derived object's configuration record
        if os.path.exists(self.derived_object):
            if not self.full:
                # clearaudit only creates a derived object if the command
                # was successful. If the command fails, either because of the command
                # itself, or due to "interference" from other processes,
                # our throwaway file is
                # only a view-private file, not a derived object. Thus, only
                # when the command succeeds can we get the configuration record.
                if cexit == 0:
                    cmd = "cleartool catcr -long " + self.derived_object
                    catcr = (run_command(cmd), self.derived_object)
                else:
                    catcr = (None, self.derived_object)

            else:
                cr_text = None

                # Attempt to get the command's return value from
                # the contents of the derived object. Do this in a
                # clearaudit shell so that our reading of the file doesn't
                # show up in a parent process's configuration record.
                # If we can't get the return value for some reason,
                # then set the return value to 255.
                cmd = "clearaudit -c 'cat " + self.derived_object + "'"
                retval_txt = run_command(cmd)
                if retval_txt:
                    try:
                        cretval = int(retval_txt[0])
                        # if the reported cretval is 0 (success) but the
                        # cretval we were told by instmake is non-success, then
                        # the command itself succeeded but clearaudit failed
                        # for some reason (including "interference")
                        if cretval == 0 and cexit != 0:
                            cr_text = AUDIT_FAILED
                    except:
                        cretval = 255
                else:
                    cretval = 255

                # Only read the audit record if the clearaudit return value was 0,
                # because if it's not 0 we know that the file is not a DO so
                # there is no audit record.
                if cexit == 0:
                    # Get the configuration record for the derived object.
                    cmd = "cleartool catcr -long " + self.derived_object
                    cr_text = run_command(cmd) 

                catcr = (cr_text, self.derived_object)

            # We no longer need this "throw-away" derived object, whose
            # sole reason for existence is to record dependency information.
            # So throw it away.
            if not self.leave_DO:
                try:
                    os.unlink(self.derived_object)
                except OSError:
                    pass

        # If the derived object does not exist there's nothing we can do.
        else:
            catcr = (None, self.derived_object)
            cretval = cexit

        return cretval, catcr



def ParseData(audit_data, log_record):
    """Read the clearaudit data and modify the LogRecord's
    input_files and output_files."""
    if not audit_data:
        return

    (catcr, derived_object) = audit_data

    if catcr == AUDIT_FAILED:
        log_record.audit_ok = False
        return

    if catcr:
        log_record.audit_ok = True
        derived_object = os.path.basename(derived_object)
        log_record.input_files, log_record.output_files = \
                analyze_catcr(catcr, derived_object)
    else:
        log_record.audit_ok = False

# derived object         /vob/foo/sys/YYY@@20-Nov.21:35.4364546 [new derived object]
re_xname      =  re.compile(r"^[^/]+(?P<filename>/.*)@@\S+")
re_xname_final = re.compile(r"^[^/]+(?P<filename>/.*)@@\S+$")

# view file              /vob/foo/sys/xyz                                     <20-Nov-02.21:45:46>
# view directory         /vob/foo/sys/DDD                                     <20-Nov-02.21:42:10> [created]
# directory version      /vob/foo/.@@/main/13                                 <09-Oct-00.13:32:46>
# version                /vob/foo/tools/rdefine@@/main/devbranch/6 <06-Aug-02.02:54:00>


# If the filename ends in a space, were hosed. The clearcase audit report
# does nothing to show use whitespace in filenames. Thats okay, because as long
# as the filename doesn't have an embedded "<", we can determine that the filename
# is supposed to have the embedded space. But we cannot determine how many
# terminating spaces the filename might have, because they're not differentiated in
# any way from the spaces that occur before the angle-bracketed timestamp.
re_timestamped_line = re.compile("^[^/]+(?P<filename>/.*\S)\s+<")

def DO_filename(line):
    """Given a line like '.... filename@@timestamp [some text]',
    return filename."""
    m = re_xname.search(line)
    if m:
        return m.group("filename")
    else:
        print >> sys.stderr, "Error: could not find derived-object filename in:", line
        return None

def timestamped_filename(line):
    """Given a line like '.... filename <timestamp>', return filename."""
    m = re_timestamped_line.search(line)
    if m:
        return m.group("filename")
    else:
        print >> sys.stderr, "Error: could not find filename in:", line
        return None

def analyze_catcr(catcr, derived_object):
    """Given the raw output of "ct catcr -long" of a derived object,
    return the list of input files and the list of output files.
    Returns a tuple of (input_files, output_files)."""

    input_files = []
    output_files = []

    # The catcr data will have lines like:

    # Target ClearAudit_Shell built by user.name
    # Host "test-host" running SunOS 5.6 (sun4u)
    # Reference Time 20-Nov-02.21:35:23, this audit started 20-Nov-02.21:35:23
    # View was test-host:/vws/bos/gilramir-ccinstmake [uuid 04b5510b.f8d711d6.b76b.00:01:83:04:6e:01]
    # Initial working directory was test-host:/vob/foo/sys
    # ----------------------------
    # MVFS objects:
    # ----------------------------
    # version                /vob/foo/tools/rdefine@@/main/devbranch/6 <06-Aug-02.02:54:00>
    # directory version      /vob/foo/.@@/main/14                            <10-Oct-00.07:33:09>
    # directory version      /vob/foo/sys@@/main/florida/6                   <28-Oct-02.10:47:12>
    # directory version      /vob/foo/sys/merge@@/main/1                  <20-Nov-02.09:42:37>
    # derived object         /vob/foo/sys/merge/mergeapi.g.c@@20-Nov.09:42.3260625 [referenced derived object]
    # derived object         /vob/foo/sys/merge/mergeapi.g.h@@20-Nov.09:42.3260626 [referenced derived object]
    # directory version      /vob/foo/.@@/main/13                                 <09-Oct-00.13:32:46>
    # directory version      /vob/foo/sys@@/main/devbranch/6                        <20-Nov-02.21:34:58>
    # derived object         /vob/foo/sys/XXX@@20-Nov.21:35.4364545 [new derived object]
    # derived object         /vob/foo/sys/YYY@@20-Nov.21:35.4364546 [new derived object]
    # derived object         /vob/foo/sys/required@@04-Feb.17:51.4754253
    # symbolic link          /vob/foo/sys/merge -> ../../bar/sys/merge
    # view symbolic link	 /vob/foo/sys/obj/shl_baz.a	      <10-Dec-02.14:40.48>
    # view private object    /vob/foo/sys/LLL                                     <20-Nov-02.21:42:49> [created]
    # derived object         /vob/foo/sys/lll@@20-Nov.21:42.4364549 [new derived object]
    # view directory         /vob/foo/sys/DDD                                     <20-Nov-02.21:42:10> [created]
    # derived object         /vob/foo/sys/ddd@@20-Nov.21:42.4364547 [new derived object]
    # derived object         /vob/foo/sys/AAA@@20-Nov.21:45.4364552 [new derived object]
    # view file              /vob/foo/sys/aaa                                     <20-Nov-02.21:45:46>

    # 0. If "version", i.e., a clear-case versioned element, it's input.
    # 1. Ignore "directory version", as we don't care about directory traversal.
    # 2. If "derived object", check for "referenced derived object" or "new derived object". Yes,
    #   if the DO is modified, it's still "new" because the timestamp is different.
    # 3. If "symbolic link", ignore. (or use "-type fd" to ignore type 'l' ... links)
    # 4. If "view private object", if "created" it's output, otherwise it's input.
    # 5. If "view file" or "view symbolic link", it's input, because any output
    #    under 'clearaudit' would have been a DO, not a "view" *anything*.
    # 6. Ignore "view directory", as we don't care about directory traversal.

    STATE_IN_HEADER = 0
    STATE_LOOKING_FOR_LAST_HEADER_LINE = 1
    STATE_DATA = 2

    state = STATE_IN_HEADER

    # Cull the lines in the configuration record for input-file and output-file
    # information.
    for line in catcr:
        # Normally we'd remove the LF at the EOL, but we extract
        # filenames via a smart regex, so there's no need to do so.

        if state == STATE_IN_HEADER:
            if line.find("MVFS objects") == 0:
                state = STATE_LOOKING_FOR_LAST_HEADER_LINE

        elif state == STATE_LOOKING_FOR_LAST_HEADER_LINE:                
            if line.find("----------------------------") == 0:
                state = STATE_DATA

        elif state == STATE_DATA:
            words = line.split()
            word0 = words[0]
            word1 = words[1]
            word2 = words[2]

            # As per #0 above
            if word0 == "version":
                input_files.append(timestamped_filename(line))

            # As per #1 above
            elif word0 == "directory" and word1 == "version":
                continue

            # As per #2 above
            elif word0 == "derived" and word1 == "object":
                # Don't record the throw-away derived object as anything.
                if line.find(derived_object) > -1:
                    continue

                if line.find("[referenced derived object]") > -1:
                    input_files.append(DO_filename(line))
                elif line.find("[new derived object]") > -1:
                    output_files.append(DO_filename(line))
                elif re_xname_final.search(line):
                    output_files.append(DO_filename(line))
                else:
                    print >> sys.stderr, "Unexpected 'derived object' line in CR: " + line

            # As per #3 above
            elif word0 == "symbolic" and word1 == "link":
                continue

            # As per #4 above
            elif word0 == "view" and word1 == "private" and word2 == "object":
                if line.find("[created]") > -1:
                    output_files.append(timestamped_filename(line))
                else:
                    input_files.append(timestamped_filename(line))

            # As per #5 above
            elif word0 == "view" and (word1 == "file" or \
        (word1 == "symbolic" and word2 == "link")):

                input_files.append(timestamped_filename(line))

            # As per #6 above
            elif word0 == "view" and word1 == "directory":
                continue

            else:
                sys.exit("Unexpected line in clearaudit report: " + line)

    return input_files, output_files
