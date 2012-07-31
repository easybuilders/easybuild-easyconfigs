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
    this test will distinguish between the different phases in the build:
       * eb-file parsing
       * initialization
       * preparation
       * pre-build verification
       * generate installdir name
       * make builddir
       * unpacking
       * patching
       * prepare toolkit
       * setup startfrom
       * configure
       * make
       * test
       * create installdir
       * make install
       * packages
       * postproc
       * sanity check
       * cleanup

    At the end of its run, this test will report which easyblocks failed (the fase and the error are included)
    via the log to stdout
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

        # Since build-order doesn't matter we don't have to use the resolveDependencies method
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
                self.test_results.append((spec, 'initialization', err))

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
        self.performStep("generate installdir name", lambda x: x.gen_installdir())
        self.performStep("make builddir", lambda x: x.make_builddir())
        self.performStep("unpacking", lambda x: x.unpack_src())
        self.performStep("patching", lambda x: x.apply_patch())
        self.performStep("prepare toolkit", lambda x: x.toolkit().prepare(x.getcfg('onlytkmod')))
        self.performStep("setup startfrom", lambda x: x.startfrom())
        self.performStep('configure', lambda x: x.configure())
        self.performStep('make', lambda x: x.make())
        self.performStep('test', lambda x: x.test())
        self.performStep('create installdir', lambda x: x.make_installdir())
        self.performStep('make install', lambda x: x.make_install())
        self.performStep('packages', lambda x: x.packages())
        self.performStep('postproc', lambda x: x.postproc())
        self.performStep('sanity check', lambda x: x.sanitycheck())
        self.performStep('cleanup', lambda x: x.cleanup())

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
