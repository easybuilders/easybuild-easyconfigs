import os
import re
import shutil

from unittest import TestCase, TestSuite
import easybuild.tools.config as config

from easybuild.tools.repository import Repository

class RepositoryTest(TestCase):

    def setUp(self):
        self.path = '/tmp/tmp-easybuild-repo'
        shutil.rmtree(self.path, True)
        os.mkdir(self.path)
        config.variables['repositoryPath'] = self.path
        self.cwd = os.getcwd()

    def runTest(self):
        repo = Repository()
        self.assertEqual(os.path.realpath(self.path), os.getcwd())

    def tearDown(self):
        del config.variables['repositoryPath']
        shutil.rmtree(self.path, True)
        os.chdir(self.cwd)

def suite():
    return TestSuite([RepositoryTest()])
