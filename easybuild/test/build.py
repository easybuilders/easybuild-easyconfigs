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
        self.errors = []

        self.log = getLog("BuildTest")

        print sys.argv[1:]
        sys.exit()

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
                self.errors.append([file, err, 'eb-file error'])

        # TODO: confirm that build-order doesn't matter
        self.apps = []
        for pkg in packages:
            spec = pkg['spec']
            name = pkg['module'][0]
            try:
                # pass None so get_class will infer it
                app_class = get_class(None, self.log, name=name)
                self.apps.append(app_class(spec, debug=True))
            except EasyBuildError, err:
                self.errors.append([spec, err, 'Initialization error'])

    def performStep(self, fase, arr, method):
        errors = 0
        for obj in arr:
            try:
                method(obj)
            except EasyBuildError, err:
                errors += 1
                # Remove this object from the array
                # we cannot continue building it
                arr.remove(obj)
                self.log.info("%s encountered error: %s (ErrorClass: %s)" % (obj, err, fase))

        self.log.info("%s errors during %s" % (errors, fase))


    def runTest(self):

        self.log.info("%s errors encountered before we can begin building" % len(self.errors))
        for (obj, err, name) in self.errors:
            self.log.info("%s encountered error: %s (ErrorClass: %s)" % (obj, err, name))

        self.errors = []

        self.log.info("Continuing building other packages")
        # take manual control over the building
        self.performStep("preparation", self.apps, lambda x: x.prepare_build())
        self.performStep("pre-build verification", self.apps, lambda x: x.ready2build())
        # TODO: might want to have more control here (so we can get better error messages
        self.performStep("build", self.apps, lambda x: x.build())

if __name__ == '__main__':
    # do not use unittest.main() as it will annoyingly parse command line arguments
    suite = unittest.TestLoader().loadTestsFromTestCase(BuildTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
