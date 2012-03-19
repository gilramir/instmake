
import sys

UNFINISHED = 'unfinished'
RESUMED    = 'resumed'
COMPLETED  = 'completed'

# This can be set to turn on special debugging during
# development. Useful if the audit_strace plugin wants to debug
# only a particular log_record.pid
debug_mode = False

class InvalidSysCallInfo(Exception):
    pass

class SysCall:
    def __init__(self, pid, name, args, retval, errmsg, state):

        self.pid        = pid
        self.name       = name
        self.args       = args
        self.retval     = retval
        self.errmsg     = errmsg
        self.state      = state


    def __repr__(self):
        return  "(PID=%s, NAME=%s, ARGS=%s, RETVAL=%s, ERRMSG=%s, STATE=%s)" % \
                (self.pid, self.name, ' '.join(self.args), self.retval,
                self.errmsg, self.state)

    def is_unfinished(self):
        return self.state == UNFINISHED

    def is_resumed(self):
        return self.state == RESUMED

    def is_completed(self):
        return self.state == COMPLETED

    def join(self, other):
        if not self.is_unfinished():
            raise InvalidSysCallInfo("%s: system call should be unfinished" % self)
            
        if not other.is_resumed():
            raise InvalidSysCallInfo("%s: system call should be resumed" % other)
            
        if self.pid  != other.pid: 
            sys.exit("CURR SYSCALL PID: %s RESUMED SYSCALL PID: %s does not match" % \
                        (self.pid, other.pid))

        if self.name != other.name:
            sys.exit("CURR SYSCALL NAME: %s RESUMED SYSCALL NAME: %s does not match" % \
                        (self.name, other.name))

        for arg in other.args:
            if not arg.isspace():
                self.args.append(arg)

        self.retval      = other.retval
        self.errmsg      = other.errmsg
        self.state       = COMPLETED


    def is_retval_negative(self):
        try:
            retval = int(self.retval)
        except:
            # if we could not determine the return value bcz it is '?'
            # or None, treat the call is success, so we may have couple of
            # false positives, but in theory they should be really rare.
#            print "Warning: %s: could not determine the retval" % self
            retval = 0

        if retval < 0:
            return True
        else:
            return False


    # system call functions, needs to be over-ridden by individual subclasses..

    def get_file_read(self):
        pass

    def get_file_written(self):
        pass

    def get_file_execed(self):
        pass

    def get_child_pid(self):
        pass

    def get_chdir_name(self):
        pass



# Add one class for each system call we want to track 
# 1) its name should be same as system call name 
# 2) it should be a subclass of SysCall.
# Override any methods for your system call.

# All the system calls should be completed. But we may get few system calls
# incompleted ( unfinished/resumed) basically strace output is missing them.
# These cases are rare, but they do occur. Do as much processing as possible to
# mine the information. 

class open(SysCall):

    def get_file_read(self):

        if self.is_completed():
            if len(self.args) < 2:
                assert "%s: Number of arguments to open system call should be atleast 2" % self
        else:
#            print "Warning %s: incomplete system call" % self
            if len(self.args) < 2:
                return None

        if self.is_retval_negative():
            return None

        fname = self.args[0]
        flags = self.args[1]

        if 'O_RDONLY' in flags or 'O_RDWR' in flags:
            fname = fname.rstrip(' "')
            fname = fname.lstrip(' "')
            return fname


    def get_file_written(self):

        if self.is_completed():
            if len(self.args) < 2:
                assert "%s: Number of arguments to open system call should be atleast 2" % self
        else:
#            print "Warning %s: incomplete system call" % self
            if len(self.args) < 2:
                return None

        if self.is_retval_negative():
            return None

        fname = self.args[0]
        flags = self.args[1]

        # anything other than O_RDONLY (O_RDWR, O_WRONLY, O_CREATE means write) 
        if 'O_RDONLY' not in flags:
            fname = fname.rstrip(' "')
            fname = fname.lstrip(' "')
            return fname


class chdir(SysCall):

    def get_chdir_name(self):
        if self.is_completed():
            if len(self.args) == 1:
                assert "%s: Number of arguments to chdir system call should be one" % self
        else:
#            print "Warning %s: incomplete system call" % self
            if len(self.args) < 1:
                return None

        if self.is_retval_negative():
            return None

        dir_name = self.args[0]
        dir_name = dir_name.rstrip(' "')
        dir_name = dir_name.lstrip(' "')
        return dir_name



class fork(SysCall):

    def get_child_pid(self):

        if self.is_unfinished():
#            print "Warning %s: incomplete system call" % self
            return None

        if self.is_retval_negative():
            return None

        return self.retval



class clone(fork):
    pass

class rename(SysCall):

    def get_file_written(self):

        if self.is_completed():
            if len(self.args) == 2:
                assert "%s: Number of arguments to chdir system call should be two" % self
        else:
#            print "Warning %s: incomplete system call" % self
            if len(self.args) < 2:
                return None

        if self.is_retval_negative():
            return None

        dest= self.args[1]
        dest= dest.rstrip(' "')
        dest= dest.lstrip(' "')
        return dest

class link(rename):
    pass

class symlink(rename):
    pass

class exec_family(SysCall):

    def get_file_execed(self):
        if debug_mode:
            print "EXEC:", self.is_completed(), self.retval, "ARGS:", self.args

        if not self.is_completed():
            return None

        if self.is_retval_negative():
            # Really we care about ENOENT (-1), but we can check for
            # any error
            return None

        if len(self.args) < 1:
            return None

        xname = self.args[0]
        xname = xname.rstrip(' "')
        xname = xname.lstrip(' "')
        return xname

class execve(exec_family):
    # 29129 execve("/bin/hostname", ["/bin/hostname"], [/* 68 vars */]) = 0
    pass
