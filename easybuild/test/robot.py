import os
from copy import deepcopy

from unittest import TestCase, TestSuite
from easybuild.tools.build_log import EasyBuildError, getLog
import easybuild.build as build
import easybuild.tools.modules as modules
from easybuild.tools.modules import Modules

orig_modules = modules.Modules
class MockModule(modules.Modules):

    def available(self, *args):
        return []

base_easyconfig_dir = "easybuild/test/easyconfigs/"

class RobotTest(TestCase):

    def setUp(self):
        # replace Modules class with something we have control over
        modules.Modules = MockModule
        build.Modules = MockModule

        self.log = getLog("RobotTest")

    def runTest(self):
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


    def tearDown(self):
        modules.Modules = orig_modules


def suite():
    return TestSuite([RobotTest()])
