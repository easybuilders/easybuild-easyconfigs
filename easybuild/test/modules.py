import os

from unittest import TestCase, TestSuite
from easybuild.tools.build_log import EasyBuildError, initLogger
import easybuild.tools.modules as modules

class ModulesTest(TestCase):

    def runTest(self):
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
    return TestSuite([ModulesTest()])


