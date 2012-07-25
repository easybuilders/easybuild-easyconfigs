import os
import re
import shutil

from unittest import TestCase, TestSuite
import easybuild.tools.config as config

from easybuild.tools.repository import FileRepository

class RepositoryTest(TestCase):

    def setUp(self):
        self.path = '/tmp/tmp-easybuild-repo'
        shutil.rmtree(self.path, True)

    def runTest(self):
        repo = FileRepository(self.path)
        self.assertEqual(repo.wc, self.path)

    def tearDown(self):
        shutil.rmtree(self.path, True)

def suite():
    return TestSuite([RepositoryTest()])
