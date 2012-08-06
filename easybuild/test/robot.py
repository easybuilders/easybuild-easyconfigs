##
# Copyright 2012 Toon Willems
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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
import os
from copy import deepcopy
from unittest import TestCase, TestSuite

import easybuild.tools.modules as modules
import easybuild.build as build
from easybuild.tools.build_log import EasyBuildError, getLog
from easybuild.tools.modules import Modules

orig_modules = modules.Modules
base_easyconfig_dir = "easybuild/test/easyconfigs/"


class MockModule(modules.Modules):
    """ MockModule class, allows for controlling what Modules() will return """

    def available(self, *args):
        """ no module should be available """
        return []


class RobotTest(TestCase):
    """ Testcase for the robot dependency resolution """

    def setUp(self):
        """ dynamically replace Modules class with MockModule """
        # replace Modules class with something we have control over
        modules.Modules = MockModule
        build.Modules = MockModule

        self.log = getLog("RobotTest")

    def runTest(self):
        """ Test with some basic testcases (also check if he can find dependencies inside the given directory """
        package = {
            'spec': '_',
            'module': ("name", "version"),
            'dependencies': []
        }
        res = build.resolveDependencies([deepcopy(package)], None, self.log)
        self.assertEqual([package], res)

        package_dep = {
            'spec': '_',
            'module': ("name", "version"),
            'dependencies': [('gzip', '1.4')]
        }
        res = build.resolveDependencies([deepcopy(package_dep)], base_easyconfig_dir, self.log)
        # Dependency should be found
        self.assertEqual(len(res), 2)

        # here we have include a Dependency in the package list
        package['module'] = ("gzip", "1.4")

        res = build.resolveDependencies([deepcopy(package_dep), deepcopy(package)], None, self.log)
        # all dependencies should be resolved
        self.assertEqual(0, sum(len(pkg['dependencies']) for pkg in res))

        # this should not resolve (cannot find gzip-1.4.eb)
        self.assertRaises(EasyBuildError, build.resolveDependencies, [deepcopy(package_dep)], None, self.log)

        # test if dependencies of an automatically found file are also loaded
        package_dep['dependencies'] = [('gzip', "1.4-GCC-4.6.3")]
        res = build.resolveDependencies([deepcopy(package_dep)], base_easyconfig_dir, self.log)

        # GCC should be first (required by gzip dependency)
        self.assertEqual(('GCC', '4.6.3'), res[0]['module'])
        self.assertEqual(('name', 'version'), res[-1]['module'])


    def tearDown(self):
        """ reset the Modules back to its original """
        modules.Modules = orig_modules


def suite():
    """ returns all the testcases in this module """
    return TestSuite([RobotTest()])
