#!/usr/bin/env python
#
# Copyright (c) 2010 by Cisco Systems, Inc.
# Gilbert Ramirez <gram@alumni.rice.edu>

import os
from distutils.core import setup
import instmakelib

man1 = "share/man/man1"

setup(
        name = "instmake",
        version = instmakelib.__version__,
        description = "Instrumented Make",
        author = "Gilbert Ramirez",
        author_email = "gram@alumni.rice.edu",
        url= "http://instmake.googlecode.com/",
        license = "BSD",
        long_description = "A tool for instrumenting make and analyzing builds.",
        packages = [ "instmakelib", "instmakeplugins" ],
        scripts = [ "instmake" ],
        data_files = [ (man1, ['doc/instmake.1']) ]
)
          
