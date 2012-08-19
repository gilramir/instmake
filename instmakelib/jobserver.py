# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Increase -j factor
"""

import os
import re

class JobServerNotAvailable(Exception):
    pass

class JobServerClient:
    re_fds = re.compile(r"(?P<r>\d+),(?P<w>\d+)")
    READ = 0
    WRITE = 1
    token = '+'
    fdstring = "--jobserver-fds="

    def __init__(self):

        # Read the environment variable
        if not os.environ.has_key(self.env_var):
            err = "%s environment variable not set." % (self.env_var,)
            raise JobServerNotAvailable(err)


        self.job_fds = [-1, -1]

        # Parse MAKEFLAGS to find jobserver filedescriptor numbers.
#        print >> sys.stderr, self.env_var, "=", os.environ[self.env_var]
        len_fdstring = len(self.fdstring)
        for arg in os.environ[self.env_var].split():
            if len(arg) > len_fdstring and \
                    arg[:len_fdstring] == self.fdstring:
                text = arg[len_fdstring:]
                m = self.re_fds.search(text)
                if not m:
                    err = "Expected \d+,\d+ in '%s'" % (text,)
                    raise JobServerNotAvailable(err)

                self.job_fds[self.READ] = int(m.group("r"))
                self.job_fds[self.WRITE] = int(m.group("w"))
                break
        else:
            # Not running jobserver? Don't do anything.
            err = "'%s' not found in %s environment variable." % \
                    (self.fdstring, self.env_var)
            raise JobServerNotAvailable(err)

    def ReadFD(self):
        return self.job_fds[self.READ]

    def WriteFD(self):
        return self.job_fds[self.WRITE]

    def EnvVar(self):
        return self.env_var

    def FDStringValue(self):
        return self.fdstring + "%d,%d" % (self.job_fds[self.READ],
                self.job_fds[self.WRITE])

    def ExportEnvVar(self):
        os.environ[self.EnvVar()] = self.FDStringValue()

    def PutToken(self, char=None):
        """Put one job token into job pipe."""
        if not char:
            char = self.token

        num_written = os.write(self.job_fds[self.WRITE], char)
        if num_written == 0:
            raise OSError

    def TakeToken(self):
        """Take one job token from pipe, possibly pending. Returns token."""
        bytes = os.read(self.job_fds[self.READ], 1)
        if bytes == "":
            # EOF
            raise OSError
        return bytes

    def PutTokens(self, numj=1, char=None):
        """Put one or more job tokens into job pipe."""
        for i in range(numj):
            self.PutToken(char)

    def TakeTokens(self, numj=1):
        """Take one or more job tokens from pipe, possibly pending."""
        for i in range(numj):
            self.TakeToken()


class GNUMakeClient(JobServerClient):
    env_var = "MAKEFLAGS"

