# Copyright (c) 2016 by Gilbert Ramirez <gramirez@a10networks.com>

import unittest

from utlib import base
from utlib import util

from instmakelib.shellsyntax import split_shell_cmdline

class CliTest(unittest.TestCase, base.TestBase):

    def test_simple(self):
        cmdline = "gcc -o x.o x.c"
        cmdv = ["gcc", "-o", "x.o", "x.c"]
        self.assertEqual(split_shell_cmdline(cmdline), cmdv)

    def test_single_quotes(self):
        cmdline = "gcc -o 'hello_world.o' 'hello_world.c'"
        cmdv = ["gcc", "-o", "hello_world.o", "hello_world.c"]
        self.assertEqual(split_shell_cmdline(cmdline), cmdv)

    def test_double_in_single(self):
        cmdline = "gcc -o x.o 'hello \" \" world.c'"
        cmdv = ["gcc", "-o", "x.o", 'hello " " world.c']
        self.assertEqual(split_shell_cmdline(cmdline), cmdv)

    def test_escaped_space(self):
        cmdline = "gcc -o x.o hello\\ world.c"
        cmdv = ["gcc", "-o", "x.o", "hello world.c"]
        self.assertEqual(split_shell_cmdline(cmdline), cmdv)

    def test_back_ticks(self):
        cmdline = "gcc -o x.o `run this`"
        cmdv = ["gcc", "-o", "x.o", "`run this`"]
        self.assertEqual(split_shell_cmdline(cmdline), cmdv)

    def test_double_in_double(self):
        cmdline = 'gcc -DPLUGINS="\\"foo bar baz\\""'
        cmdv = ["gcc", '-DPLUGINS="foo bar baz"']
        self.assertEqual(split_shell_cmdline(cmdline), cmdv)


if __name__ == '__main__':
    _test()
