"""
Parse strace output
"""
import re
import os
import sys
import types

try:
    # Called from instmake, we import like this
    from instmakelib import syscall
except ImportError:
    # But when called from the CLI, to test this code,
    # we import like this
    import syscall


SYSCALL_REGEX = re.compile(r"""
((?P<pid>\d+)\s+)?                    # PID, may or may not be present.
(?P<name>\w+)                         # system call name.
\((?P<args>.*)\)                      # args
\s+=\s+
(?P<retval>(\-?\d+|\?))               # return value
(?P<errmsg>.*)                        # errmsg ( may or may not be present)
""", re.VERBOSE)


UNFINISHED_SYSCALL_REGEX = re.compile(r"""
((?P<pid>\d+)\s+)?                    # PID, may or may not be present.
(?P<name>\w+)                         # system call name.
\((?P<args>.*)                        # args, some might present
<unfinished\s+\.\.\.>                    # unfinished
""", re.VERBOSE)


RESUMED_SYSCALL_REGEX = re.compile(r"""
((?P<pid>\d+)\s+)?                    # PID, may or may not be present.
<\.\.\.\s+
(?P<name>\w+)                         # system call name.      
\s+resumed>                         # state = resumed. 
(?P<args>.*)\)                        # args
\s+=\s+            
(?P<retval>(\-?\d+|\?))               # return value
(?P<errmsg>.*)                        # errmsg ( may or may not be present)
""", re.VERBOSE)


INFO_REGEX = re.compile(r"""
((?P<pid>\d+)\s+)?                    # PID, may or may not be present.
\-\-\-(?P<errmsg>.*)\-\-\-            # info msgs like child exited starts with ---
""", re.VERBOSE )


INFO_REGEX2 = re.compile(r"""
((?P<pid>\d+)\s+)?                    # PID, may or may not be present.
\+\+\+(?P<errmsg>.*)\+\+\+            # info msgs like child exited starts with ---
""", re.VERBOSE )


class StraceParseError(Exception):
    pass


class StraceOutput:
    def __init__(self, strace_op_data):
        assert type(strace_op_data) == types.StringType
        self.strace_op_lines = strace_op_data.split("\n")
        self.syscalls       = self.__read()
        self.process_cwd    = { }
        self.ignore_files_read = []
        self.ignore_files_written = []

        # If the very first syscall is exeve of /bin/sh, then
        # it was the sh of the cmd shell script; and we should
        # ignore that. We don't want it to appear
        # in our list of execed files.
        if len(self.syscalls) > 0:
            first_syscall = self.syscalls[0]
            if isinstance(first_syscall, syscall.exec_family):
                xname = first_syscall.get_file_execed()
                if xname == "/bin/sh":
                    self.syscalls = self.syscalls[1:]

    def set_debug(self, new_value):
        """Turn on or off debug mode in the syscall module.
        Values should be True or False"""
        syscall.debug_mode = new_value

    def remove_read(self, filename):
        self.ignore_files_read.append(filename)

    def remove_written(self, filename):
        self.ignore_files_written.append(filename)

    def __syscall_obj(self, line):
        """ parses the strace output line and returns a appropriate system call
        object """
    
        # matching a info message.
        if INFO_REGEX.match(line):
            return None
        if INFO_REGEX2.match(line):
            return None
    
        (pid, name, args, retval, errmsg, state) = self.__parse_strace_op(line)
 
        # see if the module 'syscall' has a subclass defined with syscall_name, 
        # if so return the object of syscall_name other wise return object of base
        # class syscall.SysCall
        syscall_base_class = syscall.SysCall

        if hasattr(syscall, name):
            syscall_class = getattr(syscall, name)
            if not issubclass(syscall_class, syscall_base_class):
                assert "%s is defined but it is not sub class of %s" % \
                            (syscall_class, syscall_base_class)
        else:
            syscall_class = syscall_base_class

        return syscall_class(pid, name, args, retval, errmsg, state)

            
    
    def __parse_strace_op(self, line):
        match = SYSCALL_REGEX.match(line)
        if match:
            pid    = match.group('pid')
            name   = match.group('name')
            args   = match.group('args').split(',')
            retval = match.group('retval')
            errmsg = match.group('errmsg')
            state  = syscall.COMPLETED
            return (pid, name, args, retval, errmsg, state)

        match = UNFINISHED_SYSCALL_REGEX.match(line)
        if match:
            pid    = match.group('pid')
            name   = match.group('name')
            args   = match.group('args').split(',')
            retval = None
            errmsg = None
            state  = syscall.UNFINISHED
            return (pid, name, args, retval, errmsg, state)

        match = RESUMED_SYSCALL_REGEX.match(line)
        if match:
            pid    = match.group('pid')
            name   = match.group('name')
            args   = match.group('args').split(',')
            retval = match.group('retval')
            errmsg = match.group('errmsg')
            state  = syscall.RESUMED
            return (pid, name, args, retval, errmsg, state)

        # We could not match any thing 
        raise StraceParseError("%s: Unable to parse the line" % line )


    def __read(self):
        """ read the strace output file and return a list of systemcalls. 
        Handles the unfinished and resumed system calls and returns the list of all
        system calls present in the strace ouptut in the order they have
        executed."""

        # final retval
        ret_syscalls = []
        unfinished   = { }

        for line in self.strace_op_lines:
#            print "LINE:", line
            if line == "":
                continue
            curr_syscall = self.__syscall_obj(line)

            # this line might not correspond to syscall, but rather a info
            # message
            if curr_syscall is None:
                continue

            if curr_syscall.is_completed():
                ret_syscalls.append(curr_syscall)

            # A system call is unfinished, It went to sleep before
            # completed. Add it to the return system calls and keep it
            # tracked under 'unfinished'. Once the system call finishes we
            # should update the curr_syscall.
            elif curr_syscall.is_unfinished():
                pid_name = (curr_syscall.pid, curr_syscall.name)
                unfinished[pid_name] = curr_syscall
                ret_syscalls.append(curr_syscall)

            # System call previously went to sleep resumed.
            # No, need to add to the return system calls as we already
            # added it before it went to sleep
            elif curr_syscall.is_resumed():
                pid_name = (curr_syscall.pid, curr_syscall.name)
                if unfinished.has_key(pid_name):
                    prev_syscall = unfinished[pid_name]
                    prev_syscall.join(curr_syscall)
                    del unfinished[pid_name]
                else:
                    # we got an orphaned entry :-) . Add it to the system
                    # calls list and process as much as we can do.
                    ret_syscalls.append(curr_syscall)
                    

        return ret_syscalls


    def get_files_written(self):
        return self._get_files("get_file_written", self.ignore_files_written)

    def get_files_read(self):
        return self._get_files("get_file_read", self.ignore_files_read)

    def get_files_execed(self):
        return self._get_files("get_file_execed", [])

    def _get_files(self, syscall_method_name, ignore_list):
        """Generic handler for finding files in the strace output"""
        files_result = []
        cwd = CWD()

        for syscall in self.syscalls:
            # if the system call does chdir update the cwd info.

            dir_name = syscall.get_chdir_name()
            if dir_name:
                cwd.update_cwd(syscall.pid, dir_name)
                continue

            # if the system call does fork/clone ..
            child_pid = syscall.get_child_pid()
            if child_pid:
                cwd.copy_cwd(syscall.pid, child_pid)
                continue

            if hasattr(syscall, syscall_method_name):
                syscall_method = getattr(syscall, syscall_method_name)
            else:
                continue

            fname = syscall_method()
            if fname:
                if os.path.isabs(fname):
                    abs_fname = fname
                else:
                    abs_fname = os.path.join(cwd.get_cwd(syscall.pid), fname)

                if not fname in ignore_list:
                    # Avoid duplicates
                    if not abs_fname in files_result:
                        files_result.append(abs_fname)

        return files_result




class CWD:
    """ Tracks the current working dir of the processes used in the strace output
    """

    def __init__(self):
        self.process_cwd = { }


    def get_cwd(self, pid):
        """ returns the cwd of the process pid, if the info is not available it
        initializes it to empty string and returns it. """

        # process_cwd is empty that means we are requesting the CWD for the
        # first process. We will not have that info, just start with ""
        # No need of any warning.

        if not self.process_cwd:
            self.process_cwd[pid] = ""
            return ""

        elif not self.process_cwd.has_key(pid):
            self.process_cwd[pid] = ""
#            print "Warning: CWD info for process %s not available, intializing it as empty" % pid

        return self.process_cwd[pid]

    def update_cwd(self, pid, dir_name):
        """ set the cwd of pid as dir_name """
        if os.path.isabs(dir_name):
            self.process_cwd[pid] = dir_name

        # its a relative path, so we need to add to the current CWD of the
        # process.
        else:
            curr_dir = self.get_cwd(pid)
            self.process_cwd[pid] = os.path.join(curr_dir, dir_name)

    def copy_cwd(self, parent_pid, child_pid):
        """ set the CWD of child process same as the parent process """
        self.process_cwd[child_pid] = self.get_cwd(parent_pid)


def StraceFile(filename):
    data = open(filename).read()
    return StraceOutput(data)
    
    
def _test():
    for file in sys.argv[1:]:
        data = open(file).read()
        strace_op_file = StraceOutput(data)
        print "File:", file
        print
        print "Written:"
	for i, name in enumerate(strace_op_file.get_files_written(), 1):
            print "\t%d. %s" % (i, name)
        print
        print "Read:"
	for i, name in enumerate(strace_op_file.get_files_read(), 1):
            print "\t%d. %s" % (i, name)

if __name__ == '__main__':
    _test()
