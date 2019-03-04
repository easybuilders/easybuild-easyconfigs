#!/usr/bin/python
##
# Copyright 2012-2019 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/easybuilders/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
This script is a collection of all the testcases for easybuild-easyconfigs.
Usage: "python -m easybuild.easyconfigs.test.suite.py" or "./easybuild/easyconfigs/test/suite.py"

@author: Toon Willems (Ghent University)
@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil
import sys
import tempfile
import unittest

import easybuild.tools.build_log  # noqa initialize EasyBuild logging, so we can disable it
import test.easyconfigs.easyconfigs as e
import test.easyconfigs.styletests as s
from easybuild.base import fancylogger

# disable all logging to significantly speed up tests
fancylogger.disableDefaultHandlers()
fancylogger.setLogLevelError()

# make sure no deprecated behaviour is triggered
os.environ['EASYBUILD_DEPRECATED'] = '10000'

os.environ['EASYBUILD_TMP_LOGDIR'] = tempfile.mkdtemp(prefix='easyconfigs_test_')

# call suite() for each module and then run them all
SUITE = unittest.TestSuite([x.suite() for x in [e, s]])
res = unittest.TextTestRunner().run(SUITE)

shutil.rmtree(os.environ['EASYBUILD_TMP_LOGDIR'])
del os.environ['EASYBUILD_TMP_LOGDIR']

if not res.wasSuccessful():
    sys.stderr.write("ERROR: Not all tests were successful.\n")
    sys.exit(2)
