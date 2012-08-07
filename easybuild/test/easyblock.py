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
import re

from unittest import TestCase, TestSuite
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.systemtools import get_shared_lib_ext


class EasyBlockTest(TestCase):
    """ Baseclass for easyblock testcases """

    def setUp(self):
        """ create temporary easyconfig file """
        self.eb_file = "tmp-test-file"
        f = open(self.eb_file, "w")
        f.write(self.contents)
        f.close()

    def tearDown(self):
        """ make sure to remove the temporary file """
        os.remove(self.eb_file)

    def assertErrorRegex(self, error, regex, call, *args):
        """ convenience method to match regex with the error message """
        try:
            call(*args)
        except error, err:
            self.assertTrue(re.search(regex, err.msg))


class TestEmpty(EasyBlockTest):
    """ Test empty easyblocks """

    contents = "# empty string"

    def runTest(self):
        """ empty files should not parse! """
        self.assertRaises(EasyBuildError, EasyBlock, self.eb_file)
        self.assertErrorRegex(EasyBuildError, "expected a valid path", EasyBlock, "")


class TestMandatory(EasyBlockTest):
    """ Test mandatory variable validation """

    contents = """
name = "pi"
version = "3.14"
"""

    def runTest(self):
        """ make sure all checking of mandatory variables works """
        self.assertErrorRegex(EasyBuildError, "mandatory variable \w* not provided", EasyBlock, self.eb_file)

        self.contents += "\n".join(['homepage = "http://google.com"', 'description = "test easyblock"',
                                    'toolkit = {"name": "dummy", "version": "dummy"}'])
        self.setUp()

        eb = EasyBlock(self.eb_file)

        self.assertEqual(eb['name'], "pi")
        self.assertEqual(eb['version'], "3.14")
        self.assertEqual(eb['homepage'], "http://google.com")
        self.assertEqual(eb['toolkit'], {"name":"dummy", "version": "dummy"})
        self.assertEqual(eb['description'], "test easyblock")


class TestValidation(EasyBlockTest):
    """ test other validations """

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"dummy", "version": "dummy"}
stop = 'notvalid'
"""

    def runTest(self):
        """ test other validations beside mandatory variables """
        eb = EasyBlock(self.eb_file, validate=False)
        self.assertErrorRegex(EasyBuildError, "\w* provided \w* is not valid", eb.validate)

        eb['stop'] = 'patch'
        # this should now not crash
        eb.validate()

        eb['osdependencies'] = ['non-existent-dep']
        self.assertErrorRegex(EasyBuildError, "OS dependencies were not found", eb.validate)

        # dummy toolkit, installversion == version
        self.assertEqual(eb.installversion(), "3.14")

        os.chmod(self.eb_file, 0000)
        self.assertErrorRegex(EasyBuildError, "Unexpected IOError", EasyBlock, self.eb_file)
        os.chmod(self.eb_file, 0755)

        self.contents += "\nsyntax_error'"
        self.setUp()
        self.assertErrorRegex(EasyBuildError, "SyntaxError", EasyBlock, self.eb_file)


class TestSharedLibExt(EasyBlockTest):
    """ test availability of shared_lib_ext in easyblock context """

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"dummy", "version": "dummy"}
sanityCheckPaths = { 'files': ["lib/lib.%s" % shared_lib_ext] }
"""

    def runTest(self):
        """ inside easyconfigs shared_lib_ext should be set """
        eb = EasyBlock(self.eb_file)
        self.assertEqual(eb['sanityCheckPaths']['files'][0], "lib/lib.%s" % get_shared_lib_ext())


class TestDependency(EasyBlockTest):
    """ Test parsing of dependencies """

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"GCC", "version": "4.6.3"}
dependencies = [('first', '1.1'), {'name': 'second', 'version': '2.2'}]
builddependencies = [('first', '1.1'), {'name': 'second', 'version': '2.2'}]
"""

    def runTest(self):
        """ test all possible ways of specifying dependencies """
        eb = EasyBlock(self.eb_file)
        # should include builddependencies
        self.assertEqual(len(eb.dependencies()), 4)
        self.assertEqual(len(eb.builddependencies()), 2)

        first = eb.dependencies()[0]
        second = eb.dependencies()[1]

        self.assertEqual(first['name'], "first")
        self.assertEqual(second['name'], "second")

        self.assertEqual(first['version'], "1.1")
        self.assertEqual(second['version'], "2.2")

        self.assertEqual(first['tk'], '1.1-GCC-4.6.3')
        self.assertEqual(second['tk'], '2.2-GCC-4.6.3')

        # same tests for builddependencies
        first = eb.builddependencies()[0]
        second = eb.builddependencies()[1]

        self.assertEqual(first['name'], "first")
        self.assertEqual(second['name'], "second")

        self.assertEqual(first['version'], "1.1")
        self.assertEqual(second['version'], "2.2")

        self.assertEqual(first['tk'], '1.1-GCC-4.6.3')
        self.assertEqual(second['tk'], '2.2-GCC-4.6.3')

        eb['dependencies'] = ["wrong type"]
        self.assertErrorRegex(EasyBuildError, "wrong type from unsupported type", eb.dependencies)

        eb['dependencies'] = [()]
        self.assertErrorRegex(EasyBuildError, "without name", eb.dependencies)
        eb['dependencies'] = [{'name': "test"}]
        self.assertErrorRegex(EasyBuildError, "without version", eb.dependencies)


class TestExtraOptions(EasyBlockTest):
    """ test extra options constructor """

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"GCC", "version": "4.6.3"}
toolkitopts = { "static": True}
dependencies = [('first', '1.1'), {'name': 'second', 'version': '2.2'}]
"""

    def runTest(self):
        """ extra_options should allow other variables to be stored """
        eb = EasyBlock(self.eb_file)
        self.assertRaises(KeyError, lambda: eb['custom_key'])

        extra_vars = { 'custom_key': ['default', "This is a default key"]}

        eb = EasyBlock(self.eb_file, extra_vars)
        self.assertEqual(eb['custom_key'], 'default')

        eb['custom_key'] = "not so default"
        self.assertEqual(eb['custom_key'], 'not so default')

        self.contents += "\ncustom_key = 'test'"

        self.setUp()

        eb = EasyBlock(self.eb_file, extra_vars)
        self.assertEqual(eb['custom_key'], 'test')

        eb['custom_key'] = "not so default"
        self.assertEqual(eb['custom_key'], 'not so default')

        # test if extra toolkit options are being passed
        self.assertEqual(eb.toolkit().opts['static'], True)


class TestSuggestions(EasyBlockTest):
    """ test suggestions on typos """

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"GCC", "version": "4.6.3"}
dependencis = [('first', '1.1'), {'name': 'second', 'version': '2.2'}]
"""

    def runTest(self):
        """ If a typo is present, suggestion should be provided (if possible) """
        self.assertErrorRegex(EasyBuildError, "invalid variable dependencis", EasyBlock, self.eb_file)
        self.assertErrorRegex(EasyBuildError, "suggestions: dependencies", EasyBlock, self.eb_file)


def suite():
    """ return all the tests in this file """
    return TestSuite([TestDependency(), TestEmpty(), TestExtraOptions(), TestMandatory(), TestSharedLibExt(),
        TestSuggestions(), TestValidation()])
