import os
import re

from unittest import TestCase
from easybuild.framework.easyblock import EasyBlock
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.systemtools import get_shared_lib_ext

class EasyBlockTest(TestCase):

    def setUp(self):
        self.eb_file = "tmp-test-file"
        f = open(self.eb_file, "w")
        f.write(self.contents)
        f.close()

    def tearDown(self):
        os.remove(self.eb_file)

    def assertErrorRegex(self, error, regex, call, *args):
        try:
            call(*args)
        except error, err:
            self.assertTrue(re.search(regex, err.msg))

class TestEmpty(EasyBlockTest):

    contents = "# empty string"

    def runTest(self):
        self.assertRaises(EasyBuildError, EasyBlock, self.eb_file)
        self.assertErrorRegex(EasyBuildError, "expected a valid path", EasyBlock, "")


class TestMandatory(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
"""

    def runTest(self):
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

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"dummy", "version": "dummy"}
stop = 'notvalid'
"""

    def runTest(self):
        eb = EasyBlock(self.eb_file, validate=False)
        self.assertErrorRegex(EasyBuildError, "\w* provided \w* is not valid", eb.validate)

        eb['stop'] = 'patch'
        # this should now not crash
        eb.validate()

class TestSharedLibExt(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"dummy", "version": "dummy"}
sanityCheckPaths = { 'files': ["lib/lib.%s" % shared_lib_ext] }
"""

    def runTest(self):
        eb = EasyBlock(self.eb_file)
        self.assertEqual(eb['sanityCheckPaths']['files'][0], "lib/lib.%s" % get_shared_lib_ext())

class TestDependency(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
homepage = "http://google.com"
description = "test easyblock"
toolkit = {"name":"GCC", "version": "4.6.3"}
dependencies = [('first', '1.1'), {'name': 'second', 'version': '2.2'}]
"""

    def runTest(self):
        eb = EasyBlock(self.eb_file)
        self.assertEqual(len(eb.dependencies()), 2)

        first = eb.dependencies()[0]
        second = eb.dependencies()[1]

        self.assertEqual(first['name'], "first")
        self.assertEqual(second['name'], "second")

        self.assertEqual(first['version'], "1.1")
        self.assertEqual(second['version'], "2.2")

        self.assertEqual(first['tk'], '1.1-GCC-4.6.3')
        self.assertEqual(second['tk'], '2.2-GCC-4.6.3')

