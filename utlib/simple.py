# Copyright (c) 2012 by Cisco Systems, Inc.

import unittest 

from utlib import base
from utlib import util

from instmakeplugins import print_json as IMJSON

class simpleTests(unittest.TestCase, base.TestBase):
    """
    This uses a simple makefile to test the basic
    functionality of instmake.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the workspace and reference build for this test suite"""
        cls.create_workspace("simple")
        cls.imlog, cls.makelog = cls.setup_run_instmake_build()

    def test_successful_build(self):
        """Looks for expected tool invocations in the instmake log"""
        (status, records) = self.get_instmake_records(self.imlog)

        self.assertEqual(status, util.SUCCESS, records)

        # Cound the "cp" commands
        jobs = [r for r in records if r[IMJSON.FIELD_TOOL] == "cp"]
        self.assertEqual(len(jobs), 4, records)

        # Cound the "zip" commands
        jobs = [r for r in records if r[IMJSON.FIELD_TOOL] == "zip"]
        self.assertEqual(len(jobs), 1, records)

