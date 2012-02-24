# Copyright (c) 2012 by Cisco Systems, Inc.

import unittest 

from utlib import base
from utlib import util


class simpleTests(unittest.TestCase, base.TestBase):
    """
    This uses a simple makefile to test the basic
    functionality of instmake.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the workspace and reference build for this test suite"""
        cls.create_workspace("simple")
        cls.imlog, cls.makelog = cls.run_instmake_build()

    def test_successful_build(self):
        """Looks for expected targets in the instmake log"""
        (status, output) = self.run_instmake_report(self.imlog, "ptree")

        self.assertEqual(status, util.SUCCESS, output)
    
        self.assertEqual(output.count("cp"), 4, output)
        self.assertEqual(output.count("zip"), 1, output)
