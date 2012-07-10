import os
import re
import sys

from unittest import TestCase
from easybuild.tools.build_log import getLog, EasyBuildError
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
        config.init('easybuild/easybuild_config.py')
        self.errors = []

        log = getLog("BuildTest")
        path = "easybuild/easyconfigs/"
        packages = []
        files = findEasyconfigs(path, log)
        for file in files:
            try:
                packages.extend(processEasyconfig(file, log, None))
            except EasyBuildError, err:
                self.errors.append([file, err, 'eb-file error'])

        # TODO: confirm that build-order doesn't matter
        self.apps = []
        for pkg in packages:
            spec = pkg['spec']
            name = pkg['module'][0]
            try:
                # pass None so get_class will infer it
                app_class = get_class(None, log, name=name)
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
                print "Encountered error: %s (ErrorClass: %s)" % (err, fase)

        print "%s errors during %s" % (errors, fase)


    def runTest(self):

        print "%s errors encountered before we can begin building" % len(self.errors)
        for (obj, err, name) in self.errors:
            print "%s encountered error: %s (ErrorClass: %s)" % (obj, err, name)

        self.errors = []

        print "Continuing building other packages"
        # take manual control over the building
        self.performStep("preparation", self.apps, lambda x: x.prepare_build())
        self.performStep("pre-build verification", self.apps, lambda x: x.ready2build())
        # TODO: might want to have more control here (so we can get better error messages
        self.performStep("build", self.apps, lambda x: x.build())

