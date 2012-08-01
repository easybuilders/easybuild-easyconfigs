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
import copy
import os
import re
import sys
import unittest
import xml.dom.minidom as xml

from unittest import TestCase
from easybuild.tools.build_log import getLog, EasyBuildError, initLogger
from easybuild.framework.application import get_class, Application
from easybuild.build import findEasyconfigs, processEasyconfig, resolveDependencies
from easybuild.tools.filetools import modifyEnv

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
        self.build_status = {}

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

    def performStep(self, fase, obj, method):
        """
        Perform method on object if it can be build
        """
        if obj not in self.build_status:
            try:
                method(obj)
            except EasyBuildError, err:
                # we cannot continue building it
                self.build_ok = False
                self.test_results.append((obj, fase, err))
                # keep a dict of so we can check in O(1) if objects can still be build
                self.build_status[obj] = fase

    def runTest(self):
        """
        Actual test, loop over all the different steps in a build
        """
        self.log.info("Continuing building other packages")
        base_dir = os.getcwd()
        base_env = copy.deepcopy(os.environ)

        for app in self.apps:
            # start with a clean slate
            os.chdir(base_dir)
            modifyEnv(os.environ, base_env)

            # take manual control over the building
            self.performStep("preparation", app, lambda x: x.prepare_build())
            self.performStep("pre-build verification", app, lambda x: x.ready2build())
            self.performStep("generate installdir name", app, lambda x: x.gen_installdir())
            self.performStep("make builddir", app, lambda x: x.make_builddir())
            self.performStep("unpacking", app, lambda x: x.unpack_src())
            self.performStep("patching", app, lambda x: x.apply_patch())
            self.performStep("prepare toolkit", app, lambda x: x.toolkit().prepare(x.getcfg('onlytkmod')))
            self.performStep("setup startfrom", app, lambda x: x.startfrom())
            self.performStep('configure', app, lambda x: x.configure())
            self.performStep('make', app, lambda x: x.make())
            self.performStep('test', app, lambda x: x.test())
            self.performStep('create installdir', app, lambda x: x.make_installdir())
            self.performStep('make install', app, lambda x: x.make_install())
            self.performStep('packages', app, lambda x: x.packages())
            self.performStep('postproc', app, lambda x: x.postproc())
            self.performStep('sanity check', app, lambda x: x.sanitycheck())
            self.performStep('cleanup', app, lambda x: x.cleanup())

        for result in self.test_results:
            self.log.info("%s crashed with an error during fase: %s, error: %s" % result)

        failed = len(self.build_status)
        total = len(self.apps)

        succes = [app for app in self.apps if app not in self.build_status]

        self.log.info("%s from %s packages failed to build!" % (failed, total))

        filename = "easybuild-test-output.xml"
        test_path = os.path.dirname(__file__)
        filename = os.path.join(test_path, filename)
        self.log.debug("writing xml output to %s" % filename)
        write_to_xml(succes, self.test_results, filename)

        # exit with non-zero exit-code when not build_ok
        if not self.build_ok:
            sys.exit(1)

def write_to_xml(succes, failed, filename):
    """
    Create xml output, using minimal output required according to
    http://stackoverflow.com/questions/4922867/junit-xml-format-specification-that-hudson-supports
    """
    dom = xml.getDOMImplementation()
    root = dom.createDocument(None, "testsuite", None)

    def create_testcase(name):
        el = root.createElement("testcase")
        el.setAttribute("name", name)
        return el

    def create_failure(name, error_type, error):
        el = create_testcase(name)

        # encapsulate in CDATA section
        error_text = root.createCDATASection("\n%s\n" % error)
        failure_el = root.createElement("failure")
        failure_el.setAttribute("type", error_type)
        el.appendChild(failure_el)
        el.lastChild.appendChild(error_text)
        return el

    for (obj, fase, error) in failed:
        # try to pretty print
        try:
            el = create_failure("%s/%s" % (obj.name(), obj.installversion()), fase, error)
        except:
            el = create_failure(obj, fase, error)

        root.firstChild.appendChild(el)

    for obj in succes:
        el = create_testcase("%s/%s" % (obj.name(), obj.installversion()))
        root.firstChild.appendChild(el)

    output_file = open(filename, "w")
    root.writexml(output_file, addindent="\t", newl="\n")
    output_file.close()


# do not use unittest.main() as it will annoyingly parse command line arguments
suite = unittest.TestLoader().loadTestsFromTestCase(BuildTest)
unittest.TextTestRunner(verbosity=2).run(suite)
