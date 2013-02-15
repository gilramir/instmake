# Copyright (c) 2012 by Cisco Systems, Inc.

import unittest 

from utlib import base
from utlib import util


class shellTests(unittest.TestCase, base.TestBase):
    """
    This tests how $(SHELL) works under instmake when the
    script is executable.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the workspace and reference build for this test suite"""
        cls.create_workspace("shell")

    def test_exectuable(self):
        """Using an executable script should work"""
        (status, output, imlog, makelog) = \
                self.run_instmake_build(log_prefix="executable",
                    make_opts=["executable"])

        self.assertEqual(status, util.SUCCESS, output)

    def test_not_exectuable(self):
        """Using a non-executable script should work"""
        (status, output, imlog, makelog) = \
                self.run_instmake_build(log_prefix="not-executable",
                    make_opts=["not-executable"])

        self.assertEqual(status, util.SUCCESS, output)

