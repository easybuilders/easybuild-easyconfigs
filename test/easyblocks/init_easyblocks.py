##
# Copyright 2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
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
Unit tests for initializing easyblocks.

@author: Kenneth Hoste (Ghent University)
"""

import glob
import os
import re
import tempfile
from vsc import fancylogger
from unittest import TestCase, TestLoader, main

from easybuild.framework.easyblock import get_class
from easybuild.framework.easyconfig import MANDATORY
from easybuild.framework.easyconfig.tools import get_paths_for


class InitTest(TestCase):
    """ Baseclass for easyblock testcases """

    def writeEC(self, easyblock, extratxt=''):
        """ create temporary easyconfig file """
        txt = '\n'.join([
            'easyblock = "%s"',
            'name = "foo"',
            'version = "1.3.2"',
            'homepage = "http://example.com"',
            'description = "Dummy easyconfig file."',
            'toolchain = {"name": "dummy", "version": "dummy"}',
            'sources = []',
            extratxt,
        ])

        f = open(self.eb_file, "w")
        f.write(txt % easyblock)
        f.close()

    def setUp(self):
        """ setup """
        self.log = fancylogger.getLogger("EasyblocksInitTest", fname=False)
        fd, self.eb_file = tempfile.mkstemp(prefix='easyblocks_init_test_', suffix='.eb')
        os.close(fd)

def template_init_test(self, easyblock):
    """Test whether all easyconfigs can be initialized."""

    class_regex = re.compile("^class (.*)\(.*", re.M)

    self.log.debug("easyblock: %s" % easyblock)

    # obtain easyblock class name using regex
    f = open(easyblock, "r")
    txt = f.read()
    f.close()

    res = class_regex.search(txt)
    if res:
        ebname = res.group(1)
        self.log.debug("Found class name for easyblock %s: %s" % (easyblock, ebname))

        # figure out list of mandatory variables, and define with dummy values as necessary
        app_class = get_class(ebname)
        ec_opts = app_class.extra_options()
        extra_txt = ''
        for ec_opt in ec_opts:
            if ec_opt[1][2] == MANDATORY:
                extra_txt += '%s = "foo"\n' % ec_opt[0]

        # write easyconfig file
        self.writeEC(ebname, extra_txt)

        # initialize easyblock
        # if this doesn't fail, the test succeeds
        app = app_class(self.eb_file)
    else:
        self.assertTrue(False, "Class found in easyblock %s" % easyblock)

def suite():
    """Return all easyblock initialisation tests."""

    # dynamically generate a separate test for each of the available easyblocks
    easyblocks_path = get_paths_for("easyblocks")[0]
    all_pys = glob.glob('%s/*/*.py' % easyblocks_path)
    easyblocks = [eb for eb in all_pys if not eb.endswith('__init__.py') and not '/test/' in eb]

    for easyblock in easyblocks:
        # dynamically define new inner functions that can be added as class methods to InitTest
        exec("def innertest(self): template_init_test(self, '%s')" % easyblock)
        innertest.__doc__ = "Test for initialisation of easyblock %s" % easyblock
        innertest.__name__ = "test_easyblock_%s" % '_'.join(easyblock.replace('.py', '').split('/'))
        setattr(InitTest, innertest.__name__, innertest)

    return TestLoader().loadTestsFromTestCase(InitTest)

if __name__ == '__main__':
    main()
