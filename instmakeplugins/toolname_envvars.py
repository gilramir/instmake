# Copyright (c) 2010 by Cisco Systems, Inc.
"""
ToolName plugin to remove the setting of environment variables
before the tool is invoked.
"""

import re


class Parser:

    LOOKING_FOR_ANYTHING = 0
    LOOKING_FOR_CHAR = 1
    SKIP_NEXT = 2

    expected_char = None

    quotes = "\"'\`"
    whitespace = " \t\n"


    def __init__(self, argv):
        self.cmdline = ' '.join(argv)
        self.len_cmdline = len(self.cmdline)
        self.Reset()

    def Reset(self):
        self.next_index = 0
        self.state = self.LOOKING_FOR_ANYTHING
        self.token = ''
        self.previous_state = None

    def Rest(self):
        return self.cmdline[self.next_index:]

    def GetToken(self):
        while self.next_index < self.len_cmdline:

            c = self.cmdline[self.next_index]
            self.next_index += 1

#            print "CHAR:", c
            if self.state == self.LOOKING_FOR_ANYTHING:
                if c in self.whitespace:
#                    print "WHITESPACE"
                    if self.token:
                        retval = self.token
                        self.token = ""
                        return retval

                elif c in self.quotes:
#                    print "SET LOOKING_FOR_CHAR", c
                    self.state = self.LOOKING_FOR_CHAR
                    self.expected_char = c
                    self.token += c

                elif c == "\\":
                    self.previoust_state = self.state
                    self.state = self.SKIP_NEXT
#                    print "SET SKIP_NEXT"
                    self.token += c

                elif c == ";" and self.token == "":
                    return c

                else:
                    self.token += c

            elif self.state == self.LOOKING_FOR_CHAR:
                self.token += c
                if c == self.expected_char:
                    retval = self.token
                    self.token = ""
                    self.state = self.LOOKING_FOR_ANYTHING
#                    print "SET LOOKING_FOR_ANYTHING"
                    return retval

                elif c == "\\":
                    self.previous_state = self.state
                    self.state = self.SKIP_NEXT
#                    print "SET SKIP_NEXT"
                    self.token += c

            elif self.state == self.SKIP_NEXT:
                self.token += c

        retval = self.token
        self.token = None
        return retval


def first_arg_regex_cb(first_arg, argv, cwd, m):
    LOOKING_FOR_FIRST_ARG = 0
    SKIP_NEXT = 1

    state = LOOKING_FOR_FIRST_ARG
    parser = Parser(argv)

    arg = parser.GetToken()
#    print "ARG", arg
    while arg != None:
        if state == LOOKING_FOR_FIRST_ARG:
            if "=" in arg:
                pass
            elif arg in [ ";", "&&", "||" ]:
                pass
            elif arg == "export":
                state = SKIP_NEXT
                pass
            else:
                # Use the 'arg' as the tool
#                print "RETURNING", [arg] + parser.Rest().split()
                return  [arg] + parser.Rest().split()
        elif state == SKIP_NEXT:
            state = LOOKING_FOR_FIRST_ARG
            pass

        arg = parser.GetToken()
#        print "ARG", arg


    return argv

def register(manager):
    re_set = re.compile("^\w+=")
    manager.RegisterFirstArgumentRegex(re_set, first_arg_regex_cb)
