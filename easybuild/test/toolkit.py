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

from unittest import TestCase, TestSuite
from easybuild.tools.build_log import EasyBuildError
import easybuild.tools.modules as modules
from easybuild.tools.toolkit import Toolkit
import easybuild.tools.toolkit as toolkit

# Change the Modules class so i have complete control over its behaviour
# NOTE: this heavily relies on the correct order of running tests
# This one should be run first
OrigModules = modules.Modules

class MockModule(modules.Modules):
    """ MockModule class, which mocks Modules behaviour """
    modules = []
    def available(self, name=None, *args, **kwargs):
        """ Change available to return values based on the given name """
        if name == 'gzip':
            return [('gzip', '1.4')]
        elif name == 'icc':
            return [('icc', '4.0.3-32bit')]
        else:
            return []

    def addModule(self, *args, **kwargs):
        """ convenience method, just appends to a list we can access """
        MockModule.modules.extend(*args)

    def load(self, *args, **kwargs):
        """ Modules can handle this """
        pass

    def dependencies_for(self, *args, **kwargs):
        """ customize dependencies_for to always return an empty list """
        return []

    def get_software_root(self, *args, **kwargs):
        """ this function is here so I can later replace the original """
        return "tmp"


class ToolkitTest(TestCase):
    """ testcase for Toolkit """

    def setUp(self):
        """ set some toolkit objects, replace Modules class """
        # dynamically replace Modules class
        toolkit.Modules = MockModule
        modules.Modules = MockModule
        modules.get_software_root = MockModule().get_software_root
        toolkit.get_software_root = MockModule().get_software_root

        self.tk_32bit = Toolkit("icc", "4.0.3-32bit")
        self.tk_64bit = Toolkit("GCC", "4.6.3")
        self.dummy_tk = Toolkit("dummy", "1.0")

    def runTest(self):
        """ check parsing and interaction with Modules """
        self.assertEqual(self.tk_32bit.name, 'icc')
        # assert m32flag has been set
        self.assertEqual(self.tk_32bit.m32flag, ' -m32')
        # dummy toolkit always exists
        self.assertEqual(self.dummy_tk._toolkitExists(), True)
        self.assertEqual(self.tk_32bit._toolkitExists(), True)
        self.assertEqual(self.tk_64bit._toolkitExists(), False)


        # Test get_dependency_version
        dep = {"name": "depname", "version":"1.0"}
        dep2 = {"name": "gzip", "dummy":"dummy"}

        self.assertEqual("1.0-icc-4.0.3-32bit", self.tk_32bit.get_dependency_version(dep))
        self.assertEqual('1.4', self.dummy_tk.get_dependency_version(dep2))


        # test set_options
        self.dummy_tk.set_options({'static':True, 'non-existing':False})
        self.assertEqual(self.dummy_tk.opts['static'], True)
        self.assertRaises(KeyError, lambda: self.dummy_tk.opts['non-existing'])


        # test add_dependencies
        dep = {"name": 'gzip'}
        self.tk_32bit.add_dependencies([dep])
        self.assertEqual(len(self.tk_32bit.dependencies), 1)

        self.assertRaises(EasyBuildError, self.tk_32bit.add_dependencies, [{"name":"bzip"}])

        # Test prepare
        self.assertRaises(EasyBuildError, self.tk_64bit.prepare)

        # no dependencies should be added
        self.dummy_tk.prepare()
        self.assertEqual(MockModule.modules, [])

        os.environ["EBVERSIONICC"] = "2011"
        os.environ["EBROOTICC"] = "/tmp"

        self.tk_32bit.prepare()

        self.assertEqual(MockModule.modules, [(self.tk_32bit.name, self.tk_32bit.version), dep])
        MockModule.modules = []

    def tearDown(self):
        """ reset Modules to its original """
        modules.Modules = OrigModules

def suite():
    """ returns all the testcases in this module """
    return TestSuite([ToolkitTest()])
