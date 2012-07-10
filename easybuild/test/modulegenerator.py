import os
import re

from unittest import TestCase, TestSuite
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.module_generator import ModuleGenerator
from easybuild.framework.application import Application

class ModuleGeneratorTest(TestCase):

    def setUp(self):
        # TODO: include gzip.eb as test file
        self.modgen = ModuleGenerator(Application('easybuild/test/gzip.eb'))
        self.modgen.app.installdir = "/tmp"

    def runTest(self):
        expected = """#%Module

proc ModulesHelp { } {
    puts stderr {   gzip (GNU zip) is a popular data compression program as a replacement for compress - Homepage: http://www.gzip.org/
}
}

module-whatis {gzip (GNU zip) is a popular data compression program as a replacement for compress - Homepage: http://www.gzip.org/}

set root    /tmp

conflict    gzip
"""

        desc = self.modgen.getDescription()
        self.assertEqual(desc, expected)

        # test loadModule
        expected = """
if { ![is-loaded name/version] } {
    module load name/version
}
"""
        self.assertEqual(expected, self.modgen.loadModule("name", "version"))

        # test unloadModule
        expected = """
if { ![is-loaded name/version] } {
    if { [is-loaded name] } {
        module unload name
    }
}
"""
        self.assertEqual(expected, self.modgen.unloadModule("name", "version"))

        # test prependPaths
        expected = """prepend-path	key		$root/path1
prepend-path	key		$root/path2
"""
        self.assertEqual(expected, self.modgen.prependPaths("key", ["path1", "path2"]))

        # test setEnvironment
        self.assertEqual("setenv\tkey\t\tvalue\n", self.modgen.setEnvironment("key", "value"))

def suite():
    return TestSuite([ModuleGeneratorTest()])
