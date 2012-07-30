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
    modules = []
    def available(self, name=None, *args):
        if name == 'gzip':
            return [('gzip', '1.4')]
        elif name == 'icc':
            return [('icc', '4.0.3-32bit')]
        else:
            return []

    def addModule(self, *args):
        MockModule.modules.extend(*args)

    def load(*args):
        pass

    def dependencies_for(*args):
        return []

    def get_software_root(*args):
        return "tmp"


class ToolkitTest(TestCase):

    def setUp(self):
        # dynamically replace Modules class
        toolkit.Modules = MockModule
        modules.Modules = MockModule
        modules.get_software_root = MockModule().get_software_root
        toolkit.get_software_root = MockModule().get_software_root

        self.tk_32bit = Toolkit("icc", "4.0.3-32bit")
        self.tk_64bit = Toolkit("GCC", "4.6.3")
        self.dummy_tk = Toolkit("dummy", "1.0")

    def runTest(self):
        self.assertEqual(self.tk_32bit.name, 'icc')
        # assert m32flag has been set
        self.assertEqual(self.tk_32bit.m32flag, ' -m32')
        # dummy toolkit always exists
        self.assertEqual(self.dummy_tk._toolkitExists(), True)
        self.assertEqual(self.tk_32bit._toolkitExists(), True)
        self.assertEqual(self.tk_64bit._toolkitExists(), False)


        # Test getDependencyVersion
        dep = {"name": "depname", "version":"1.0"}
        dep2 = {"name": "gzip", "dummy":"dummy"}

        self.assertEqual("1.0-icc-4.0.3-32bit", self.tk_32bit.getDependencyVersion(dep))
        self.assertEqual('1.4', self.dummy_tk.getDependencyVersion(dep2))


        # test setOptions
        self.dummy_tk.setOptions({'static':True, 'non-existing':False})
        self.assertEqual(self.dummy_tk.opts['static'], True)
        self.assertRaises(KeyError, lambda: self.dummy_tk.opts['non-existing'])


        # test addDependencies
        dep = {"name": 'gzip'}
        self.tk_32bit.addDependencies([dep])
        self.assertEqual(len(self.tk_32bit.dependencies), 1)

        self.assertRaises(EasyBuildError, self.tk_32bit.addDependencies, [{"name":"bzip"}])

        # Test prepare
        self.assertRaises(EasyBuildError, self.tk_64bit.prepare)

        # no dependencies should be added
        self.dummy_tk.prepare()
        self.assertEqual(MockModule.modules, [])

        os.environ["SOFTVERSIONICC"] = "2011"
        os.environ["SOFTROOTICC"] = "/tmp"

        self.tk_32bit.prepare()

        self.assertEqual(MockModule.modules, [(self.tk_32bit.name, self.tk_32bit.version), dep])
        MockModule.modules = []

    def tearDown(self):
        modules.Modules = OrigModules

def suite():
    return TestSuite([ToolkitTest()])
