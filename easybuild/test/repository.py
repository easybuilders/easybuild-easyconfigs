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
import shutil
from unittest import TestCase, TestSuite

from easybuild.tools.repository import FileRepository


class RepositoryTest(TestCase):
    """ very basis FileRepository test, we don't want git / svn dependency """

    def setUp(self):
        """ make sure temporary path does not exist """
        self.path = '/tmp/tmp-easybuild-repo'
        shutil.rmtree(self.path, True)

    def runTest(self):
        """ after initialization it should be the working copy """
        repo = FileRepository(self.path)
        self.assertEqual(repo.wc, self.path)

    def tearDown(self):
        """ clean up after myself """
        shutil.rmtree(self.path, True)

def suite():
    """ returns all the testcases in this module """
    return TestSuite([RepositoryTest()])
