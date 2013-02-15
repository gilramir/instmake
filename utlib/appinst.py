# Copyright (c) 2012 by Cisco Systems, Inc.

import unittest 

from utlib import base
from utlib import util


class appinstTests(unittest.TestCase, base.TestBase):
    """
    This tests the app instrumentation feature of instmake,
    in which instrumented commands can add fields to their instmake
    records.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the workspace and reference build for this test suite"""
        cls.create_workspace("appinst")

        cls.imlog, cls.makelog = cls.setup_run_instmake_build()

    def test_string_aaa(self):
        """Looks for expected targets in the instmake log"""
        (status, output) = self.run_instmake_report(self.imlog, "grep",
                report_opts=["--cmdline", "aaa"])

        self.assertEqual(status, util.SUCCESS, output)
        text = "'string':  aaa"
        self.assertEqual(output.count(text), 1, output)

    def test_string_bbb(self):
        """Looks for expected targets in the instmake log"""
        (status, output) = self.run_instmake_report(self.imlog, "grep",
                report_opts=["--cmdline", "bbb"])

        self.assertEqual(status, util.SUCCESS, output)
        text = "'string':  bbb"
        self.assertEqual(output.count(text), 1, output)
