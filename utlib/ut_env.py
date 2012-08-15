# Copyright (c) 2012 by Cisco Systems, Inc.

import os
import random
import unittest 

from utlib import base
from utlib import util

MAGIC_COOKIE = "INSTMAKE_UNIT_TEST_COOKIE"

class envTests(unittest.TestCase, base.TestBase):
    """
    Test the 'env' audit plugin.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the workspace and reference build for this test suite"""

        random.seed()
        cls.magic_cookie = str(random.random())
        os.environ[MAGIC_COOKIE] = cls.magic_cookie

        cls.create_workspace("env")
        cls.imlog, cls.makelog = cls.setup_run_instmake_build(
                instmake_opts=["-a", "env"])

    def test_successful_build(self):
        """Looks for expected targets in the instmake log"""
        (status, output) = self.run_instmake_report(self.imlog, "ptree")

        self.assertEqual(status, util.SUCCESS, output)
    
        self.assertEqual(output.count("cp"), 4, output)
        self.assertEqual(output.count("zip"), 1, output)

    def test_find_magic_cookie(self):
        """Looks for the magic cookie in the environment variables"""
        (status, output) = self.run_instmake_report(self.imlog, "dump")

        magic_lines = [line for line in output.split("\n")
                if line.find(MAGIC_COOKIE) != -1]

        self.assertTrue(len(magic_lines) > 0)
   
        # Just check the first line; that's enough.
        first_line = magic_lines[0]

        self.assertNotEqual(first_line.find(self.magic_cookie), -1)
