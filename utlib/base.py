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
    def create_workspace(cls, name):
        """Create a workspace directory for a test class."""
        # Where the checked-in files for this unit-test are located
        cls.utfiles_dir = os.path.join(TOP_CWD, UTFILES, name)

        # The root dir of the temp workspace for this test suite
        cls.ws_dir = os.path.join(TEST_ROOT, name)

        # The root dir of the temp workspace for this test suite
        cls.ws_build_dir = os.path.join(TEST_ROOT, name, BUILD_DIR)

        # Remove it if it exists
        if os.path.exists(cls.ws_dir):
            if os.path.isdir(cls.ws_dir):
                shutil.rmtree(cls.ws_dir)
            else:
                os.remove(cls.ws_dir)

        # Make the directory
        os.makedirs(cls.ws_dir)

        # Copy sources into the build dir
        shutil.copytree(cls.utfiles_dir, cls.ws_build_dir)

    @classmethod
    def setup_run_instmake_build(cls, instmake_opts=None, make=DEFAULT_MAKE,
            make_opts=None, log_prefix=None):
        """Run an instmake build. This is meant to be run
        in the setUpClass class method. It asserts on the success
        of the builds, since the build needs to succeed for the
        rest of the tests to work, which check the reports.
        
        Returns a tuple:
            (instmake-log path, make-log path)
        """

        (retval, output, instmake_log, make_log) = \
            cls.run_instmake_build(instmake_opts, make,
                    make_opts, log_prefix)

        assert retval == util.SUCCESS, ' '.join(cmdv) + "\n" +  output

        return instmake_log, make_log


    @classmethod
    def run_instmake_build(cls, instmake_opts=None, make=DEFAULT_MAKE,
            make_opts=None, log_prefix=None):
        """Run an instmake build. Returns a tuple:
            (retval, output, instmake-log path, make-log path)
            
            Although this is a classmethod, is meant to be run
            from a TestCase instance. The idea is that multiple
            tests in a TestCase would want to run a build.
            You can differentiate them with log_prefix, to save
            to differnet log files."""

        if instmake_opts == None:
            instmake_opts = []

        if make_opts == None:
            make_opts = []

        if log_prefix == None:
            log_prefix = DEFAULT_LOG

        assert type(instmake_opts) == types.ListType, instmake_opts
        assert type(make) == types.StringType, make
        assert type(make_opts) == types.ListType, make_opts
        assert "-C" not in make_opts, "Already uses -C"

        log_base = os.path.join(cls.ws_dir, log_prefix)

        cmdv = [ INSTMAKE, "--logs", log_base ] + instmake_opts + \
                [ make, "-C", cls.ws_build_dir ] + make_opts
        
        # Run the instmake build
        (retval, output) = util.exec_cmdv(cmdv)

        return (retval, output, 
            log_base + IMLOG_SUFFIX,
            log_base + MKLOG_SUFFIX)


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

        cmdv = [ INSTMAKE, "-L", imlog] + instmake_opts + \
                [ "-s", report ] + report_opts
        
        # Run the instmake build
        (retval, output) = util.exec_cmdv(cmdv)
        return retval, output
