# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Routines for interacting with ClearCase cleartool.
"""

import re
from instmakelib import pexpect

class ClearToolError(Exception):
        pass

class ClearTool:
        """
        Maintains a running cleartool process. You can send
        commands to the process, and the results are returned
        to you. This is more efficient than invoking a new
        cleartool process each time you need one.
        """

        re_error = re.compile("cleartool: Error: (?P<errmsg>.*)\n")

        def __init__(self):
            try:
                self.ct = pexpect.spawn("cleartool")
            except pexpect.ExceptionPexpect, err:
                raise ClearToolError(err)

            self.ct.expect("cleartool> ")
            self.at_prompt = 1

        def Close(self):
            self.ct.close_wait()

        def Run(self, cmd, *args):
                """
                Send a command to our cleartool process, and return the result.
                A ClearToolError is raised if cleartool reports
                an error with the command.
                Any args passed are joined with "cmd" with intervening
                whitespace.
                """
                assert self.at_prompt

                cmd_text = cmd + " " 
                if args:
                        cmd_text += " ".join(args)

                self.at_prompt = 0
                self.ct.sendline(cmd_text)

                return self._readlines()

        def _readlines(self):
                """
                Read lines until the next cleatool> prompt appears.
                """
                self.ct.expect("\ncleartool> ")
                text = self.ct.before
                self.at_prompt = 1

                # Look for error message
                m = self.re_error.search(text)
                if m:
                        raise ClearToolError(m.group('errmsg'))

                # This splits the text into multiple lines, *and*
                # removes the linefeeds.
                lines = map(lambda x: x[:-1], text.split("\n"))
           
                # The first line contains our command. Remove it.
                return lines[1:]
