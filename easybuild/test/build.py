import os
import re
import sys
import unittest

from unittest import TestCase
from easybuild.tools.build_log import getLog, EasyBuildError, initLogger
from easybuild.framework.application import get_class, Application
from easybuild.build import findEasyconfigs, processEasyconfig, resolveDependencies

import easybuild.tools.config as config

class BuildTest(TestCase):
    """
    This class will build everything in the path given to it.
    There are several possibilities why some applications fail to build,
    this test will try to distinguish between: 'eb-file error', 'preparation error', 'configure',
    'make', 'make install', 'sanitycheck', 'test'
    """

    def setUp(self):
        """ fetch application instances, report eb-file errors """
        logFile, log, hn = initLogger(filename=None, debug=True, typ=None)

        config.init('easybuild/easybuild_config.py')
        self.test_results = []

        self.log = getLog("BuildTest")
        self.build_ok = True

        files = []
        if len(sys.argv) > 1:
            for path in sys.argv[1:]:
                files += findEasyconfigs(path, log)
        else:
            # Default path
            path = "easybuild/easyconfigs/"
            files = findEasyconfigs(path, log)

        packages = []
        for file in files:
            try:
                packages.extend(processEasyconfig(file, self.log, None))
            except EasyBuildError, err:
                self.build_ok = False
                self.test_results.append((file, 'eb-file error', err))

        # TODO: confirm that build-order doesn't matter
        self.apps = []
        for pkg in packages:
            spec = pkg['spec']
            name = pkg['module'][0]
            try:
                # handle easyconfigs with custom easyblocks
                easyblock = None
                reg = re.compile(r"^\s*easyblock\s*=(.*)$")
                for line in open(spec).readlines():
                    match = reg.search(line)
                    if match:
                        easyblock = eval(match.group(1))
                        break

                app_class = get_class(easyblock, self.log, name=name)
                self.apps.append(app_class(spec, debug=True))
            except EasyBuildError, err:
                self.build_ok = False
                self.test_results.append((spec, 'Initialization error', err))

    def performStep(self, fase, method):
        errors = 0
        new_apps = []
        for obj in self.apps:
            try:
                method(obj)
                new_apps.append(obj)
            except EasyBuildError, err:
                errors += 1
                # we cannot continue building it
                self.build_ok = False
                self.test_results.append((obj, fase, err))

        self.apps = new_apps

        self.log.info("%s errors during %s" % (errors, fase))


    def runTest(self):

        self.log.info("Continuing building other packages")
        # take manual control over the building
        self.performStep("preparation", lambda x: x.prepare_build())
        self.performStep("pre-build verification", lambda x: x.ready2build())
        self.performStep("build", lambda x: x.build())

        # At this stage, self.apps contains the succesfully build packages

        for result in self.test_results:
            self.log.info("%s crashed with an error during fase: %s, error: %s" % result)

        failed = len(self.test_results)
        total = failed + len(self.apps)

        self.log.info("%s from %s packages failed to build!" % (failed, total))

        # exit with non-zero exit-code when not build_ok
        if not self.build_ok:
            sys.exit(1)

if __name__ == '__main__':
    # do not use unittest.main() as it will annoyingly parse command line arguments
    suite = unittest.TestLoader().loadTestsFromTestCase(BuildTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
