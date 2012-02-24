# Copyright (c) 2012 by Cisco Systems, Inc.

import os
import shutil
import types

from utlib import util

TOP_CWD = os.getcwd()
TEST_ROOT = os.path.join(TOP_CWD, "tmp")
UTFILES = "utfiles"
BUILD_DIR = "build"

INSTMAKE = "./instmake"

DEFAULT_MAKE = "make"
DEFAULT_LOG = "default"
IMLOG_SUFFIX = ".imlog"
MKLOG_SUFFIX = ".make.out"

class TestBase:
    @classmethod
    def create_workspace(self, name):
        """Create a workspace directory for a test class."""
        # Where the checked-in files for this unit-test are located
        self.utfiles_dir = os.path.join(TOP_CWD, UTFILES, name)

        # The root dir of the temp workspace for this test suite
        self.ws_dir = os.path.join(TEST_ROOT, name)

        # The root dir of the temp workspace for this test suite
        self.ws_build_dir = os.path.join(TEST_ROOT, name, BUILD_DIR)

        # Remove it if it exists
        if os.path.exists(self.ws_dir):
            if os.path.isdir(self.ws_dir):
                shutil.rmtree(self.ws_dir)
            else:
                os.remove(self.ws_dir)

        # Make the directory
        os.makedirs(self.ws_dir)

        # Copy sources into the build dir
        shutil.copytree(self.utfiles_dir, self.ws_build_dir)

    @classmethod
    def run_instmake_build(self, instmake_opts=None, make=DEFAULT_MAKE,
            make_opts=None):
        """Run an instmake build"""

        if instmake_opts == None:
            instmake_opts = []

        if make_opts == None:
            make_opts = []

        assert type(instmake_opts) == types.ListType, instmake_opts
        assert type(make) == types.StringType, make
        assert type(make_opts) == types.ListType, make_opts
        assert "-C" not in make_opts, "Already uses -C"

        log_base = os.path.join(self.ws_dir, DEFAULT_LOG)

        cmdv = [ INSTMAKE, "--logs", log_base ] + instmake_opts + \
                [ make, "-C", self.ws_build_dir ] + make_opts
        
        # Run the instmake build
        (retval, output) = util.exec_cmdv(cmdv)
        assert retval == util.SUCCESS, ' '.join(cmdv) + "\n" +  output

        return log_base + IMLOG_SUFFIX, log_base + MKLOG_SUFFIX



    def run_instmake_report(self, imlog, report, instmake_opts=None,
            report_opts=None):
        """Run an instmake build"""

        if instmake_opts == None:
            instmake_opts = []

        if report_opts == None:
            report_opts = []

        assert type(imlog) == types.StringType, imlog
        assert type(instmake_opts) == types.ListType, instmake_opts
        assert type(report) == types.StringType, report
        assert type(report_opts) == types.ListType, report_opts

        log_base = os.path.join(self.ws_dir, DEFAULT_LOG)

        cmdv = [ INSTMAKE, "-L", imlog] + instmake_opts + \
                [ "-s", report ] + report_opts
        
        # Run the instmake build
        (retval, output) = util.exec_cmdv(cmdv)
        return retval, output
