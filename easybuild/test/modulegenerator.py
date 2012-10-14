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

from unittest import TestCase, TestSuite
from easybuild.tools.module_generator import ModuleGenerator
from easybuild.framework.easyblock import EasyBlock


class ModuleGeneratorTest(TestCase):
    """ testcase for ModuleGenerator """

    def setUp(self):
        """ initialize ModuleGenerator with test Application """
        self.modgen = ModuleGenerator(EasyBlock('easybuild/test/easyconfigs/gzip-1.4.eb'))
        self.modgen.app.installdir = "/tmp"

    def runTest(self):
        """ since we set the installdir above, we can predict the output """
        expected = """#%Module

proc ModulesHelp { } {
    puts stderr {   gzip (GNU zip) is a popular data compression program as a replacement for compress - Homepage: http://www.gzip.org/
}
}

module-whatis {gzip (GNU zip) is a popular data compression program as a replacement for compress - Homepage: http://www.gzip.org/}

set root    /tmp

conflict    gzip
"""

        desc = self.modgen.get_description()
        self.assertEqual(desc, expected)

        # test loadModule
        expected = """
if { ![is-loaded name/version] } {
    module load name/version
}
"""
        self.assertEqual(expected, self.modgen.load_module("name", "version"))

        # test unloadModule
        expected = """
if { ![is-loaded name/version] } {
    if { [is-loaded name] } {
        module unload name
    }
}
"""
        self.assertEqual(expected, self.modgen.unload_module("name", "version"))

        # test prependPaths
        expected = """prepend-path	key		$root/path1
prepend-path	key		$root/path2
"""
        self.assertEqual(expected, self.modgen.prepend_paths("key", ["path1", "path2"]))

        # test setEnvironment
        self.assertEqual("setenv\tkey\t\tvalue\n", self.modgen.set_environment("key", "value"))

def suite():
    """ returns all the testcases in this module """
    return TestSuite([ModuleGeneratorTest()])
