import os
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

class TestEmpty(EasyBlockTest):

    contents = "# empty string"

    def runTest(self):
        self.assertRaises(EasyBuildError, EasyBlock, self.eb_file)


class TestMandatory(EasyBlockTest):

    contents = """
name = "pi"
version = "3.14"
"""

    def runTest(self):
        self.assertRaises(EasyBuildError, EasyBlock, self.eb_file)
        self.contents += "\n".join(['homepage = "http://google.com"', 'description = "test easyblock"',
                                    'toolkit = {"name": "dummy", "version": "dummy"}'])
        self.setUp()

        eb = EasyBlock(self.eb_file)

        self.assertEqual(eb['name'], "pi")
        self.assertEqual(eb['version'], "3.14")
        self.assertEqual(eb['homepage'], "http://google.com")
        self.assertEqual(eb['toolkit'], {"name":"dummy", "version": "dummy"})
        self.assertEqual(eb['description'], "test easyblock")

