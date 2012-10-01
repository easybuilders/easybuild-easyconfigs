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

import easybuild.tools.modules as modules
from unittest import TestCase, TestSuite


class ModulesTest(TestCase):
    """ small test for Modules """

    def runTest(self):
        """ test if we load one module it is in the loaded_modules """
        testmods = modules.Modules()
        ms = testmods.available('', None)
        if len(ms) != 0:
            import random
            m = random.choice(ms)
            testmods.addModule([m])
            testmods.load()

            tmp = {"name": m[0], "version": m[1]}
            assert(tmp in testmods.loaded_modules())

def suite():
    """ returns all the testcases in this module """
    return TestSuite([ModulesTest()])


