import os
import re

from unittest import TestCase
from easybuild.framework.easy_block import EasyBlock
from easybuild.tools.build_log import EasyBuildError

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
stop = 'not-valid'
"""

    def runTest(self):
        eb = EasyBlock(self.eb_file, validate=False)
        self.assertErrorRegex(EasyBuildError, "\w* provided \S* is not valid", eb.validate)

        eb['stop'] = 'patch'
        # this should now not crash
        eb.validate()

