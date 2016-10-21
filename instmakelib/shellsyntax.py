# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Parse Unix Shell syntax.
"""

import sys

class UnbalancedQuotes(Exception):
    pass

def split_shell_cmdline(cmdline, leave_quotes=0):
    """Given a string representing a shell command-line,
    split arguments into a list. Special chars like single-
    and double-quotes are honored. Can raise UnbalancedQutoes."""

    STATE_NORMAL = 0
    STATE_QUOTE = 1
    STATE_ESCAPE = 4
    STATE_WHITESPACE = 5

    argv = []
    states = []
    state = STATE_NORMAL
    current_arg = None
    qchar = None

    for c in cmdline:

        # First check for the whitespace state because we may
        # want to change state and keep on processing, instead of
        # looping to the next character.
        if state == STATE_WHITESPACE:
            if c == " " or c == "\t" or c == "\n":
                continue
            else:
                # Don't push state; we replace current state.
                state = STATE_NORMAL
                # fall through to next if-block.

        # If we're in a normal state, look for special characters
        # and for the comment hash mark, which we will use as the
        # cut-off point.
        if state == STATE_NORMAL:
#            print "NORMAL c=(%s)" % (c,)
            if c == "'" or c == '"' or c == '`':
                states.append(state)
                state = STATE_QUOTE
                qchar = c

                if leave_quotes or c == '`':
                    if current_arg == None:
                        current_arg = c
                    else:
                        current_arg += c

            elif c == '\\':
                states.append(state)
                state = STATE_ESCAPE

            elif c == "#":
                if leave_quotes and current_arg == None:
                    current_arg = c
                break

            elif c == " " or c == "\t" or c == "\n":
                if current_arg != None:
                    argv.append(current_arg)
#                    print "APPEND ARG (%s)" % (current_arg,)
                    current_arg = None

                # Don't push state; we replace current state.
                state = STATE_WHITESPACE

            else:
                if current_arg == None:
                    current_arg = c
                else:
                    current_arg += c


        # Nothing is special inside single quotes excpet another single quote.
        elif state == STATE_QUOTE:
#            print "QUOTE c=(%s)" % (c,)
            if c == qchar:
                try:
                    state = states.pop()
                except IndexError:
                    return cmdline

                if leave_quotes or c == '`':
                    if current_arg == None:
                        current_arg = c
                    else:
                        current_arg += c

            elif c == '\\':
                states.append(state)
                state = STATE_ESCAPE

            else:
                if current_arg == None:
                    current_arg = c
                else:
                    current_arg += c


        # The escape state lasts for only one character.
        # Just pop the old state.
        elif state == STATE_ESCAPE:
#            print "ESC c=(%s)" % (c,)
            if c in [ "r", "n" ]:
                c = '\\' + c

            if current_arg == None:
                current_arg = c
            else:
                current_arg += c

            try:
                state = states.pop()
#                print "CURRENT_ARG: (%s) state=%s" % (current_arg, state)
            except IndexError:
                return cmdline

        else:
            sys.exit("Text.split_shell_cmdline:state %s not expected" % (state,))

    if current_arg != None:
        argv.append(current_arg)

    return argv



def remove_trailing_comment(cmdline):
    """Given a command-line, removes any trailing comment. Returns
    the new command-line, whether there was a trailing comment or not.
    Honors quotes, but doesn't raise UnbalancedQuote as it just cares
    about trailing comments."""

    STATE_NORMAL = 0
    STATE_SINGLE_QUOTE = 1
    STATE_DOUBLE_QUOTE = 2
    STATE_BACKTICK = 3
    STATE_ESCAPE = 4

    states = []
    state = STATE_NORMAL
    num_chars_to_copy = 0

    for c in cmdline:
        # If we're in a normal state, look for special characters
        # and for the comment hash mark, which we will use as the
        # cut-off point.
        if state == STATE_NORMAL:
            if c == "'":
                states.append(state)
                state = STATE_SINGLE_QUOTE
            elif c == '"':
                states.append(state)
                state = STATE_DOUBLE_QUOTE
            elif c == '`':
                states.append(state)
                state = STATE_BACKTICK
            elif c == '\\':
                states.append(state)
                state = STATE_ESCAPE
            elif c == "#":
                break

        # Nothing is special inside single quotes excpet another single quote. 
        elif state == STATE_SINGLE_QUOTE:
            if c == "'":
                try:
                    state = states.pop()
                except IndexError:
                    return cmdline

        # Inside double quotes, honor some things.
        elif state == STATE_DOUBLE_QUOTE:
            if c == '"':
                try:
                    state = states.pop()
                except IndexError:
                    return cmdline
            elif c == '\\':
                states.append(state)
                state = STATE_ESCAPE
            elif c == '`':
                states.append(state)
                state = STATE_BACKTICK

        # Backtick's basically act like the NORMAL state
        elif state == STATE_BACKTICK:
            if c == "'":
                states.append(state)
                state = STATE_SINGLE_QUOTE
            elif c == '"':
                states.append(state)
                state = STATE_DOUBLE_QUOTE
            elif c == '`':
                try:
                    state = states.pop()
                except IndexError:
                    return cmdline
            elif c == '\\':
                states.append(state)
                state = STATE_ESCAPE

        # The escape state lasts for only one character.
        # Just pop the old state.
        elif state == STATE_ESCAPE:
                try:
                    state = states.pop()
                except IndexError:
                    return cmdline

        else:
            sys.exit("Text.remove_trailing_comment:state %s not expected" % (state,))

        num_chars_to_copy += 1

    if states:
        return cmdline
    else:
        return cmdline[:num_chars_to_copy]


def _test():

    def _ssc_test(text):
        print "CMDLINE:", text
        print "RESULT :", split_shell_cmdline(text)
        print

    _ssc_test("gcc -o x.o x.c")
    _ssc_test("gcc -o 'hello world.o' 'hello world.c'")
    _ssc_test("gcc -o x.o 'hello \" \" world.c'")
    _ssc_test("gcc -o x.o hello\\ world.c")
    _ssc_test("gcc -o x.o `run this`")


if __name__ == '__main__':
    _test()
