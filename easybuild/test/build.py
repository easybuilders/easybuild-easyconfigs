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
import logging
import platform
import os
import re
import sys
import time
import unittest
import xml.dom.minidom as xml
from datetime import datetime
from optparse import OptionParser
from unittest import TestCase

import easybuild
import easybuild.tools.config as config
import easybuild.tools.systemtools as systemtools
import easybuild.tools.build_log as build_log
from easybuild.tools.build_log import getLog, EasyBuildError, initLogger
from easybuild.framework.application import get_class, Application
from easybuild.build import findEasyconfigs, processEasyconfig, resolveDependencies
from easybuild.tools.filetools import modifyEnv
from easybuild.tools.pbs_job import PbsJob


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
        self.build_stopped = {}
        self.succes = []
        self.cur_dir = os.getcwd()

        self.log = getLog("BuildTest")
        self.build_ok = True
        self.parallel = False
        self.jobs = []

        parser = OptionParser()
        parser.add_option("--job", action="store_true", dest="parallel",
                  help="submit jobs to build in parallel")
        parser.add_option("--output-file", dest="filename", help="submit jobs to build in parallel")

        (opts, args) = parser.parse_args()
        self.parallel = opts.parallel

        # Create base directory inside the current directory. This will be used to place
        # all log files and the test output as xml
        basename = "easybuild-test-%s" % datetime.now().strftime("%d-%m-%Y-%H:%M:%S")
        if opts.filename:
            filename = os.path.abspath(opts.filename)
        elif "EASYBUILDTESTOUTPUT" in os.environ:
            filename = os.environ["EASYBUILDTESTOUTPUT"]
        else:
            filename = os.path.join(self.cur_dir, basename, "easybuild-test.xml")

        self.output_file = filename
        self.output_dir = os.path.dirname(self.output_file)

        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir)

        # find all easyconfigs (either in specified paths or in 'easybuild/easyblocks')
        files = []
        if args:
            for path in args:
                files += findEasyconfigs(path, log)
        else:
            # Default path
            path = "easybuild/easyconfigs/"
            files = findEasyconfigs(path, log)

        # if we want to build with jobs, we should do it now, since we have very little time on the login node
        if self.parallel:
            # this method will submit the jobs, in runTest we will handle the aggregation of the results
            self.submit_jobs(files)
            return

        # process all the found easyconfig files
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

    def submit_jobs(self, files):
        """
        Build the given files in parallel by submitting jobs
        """
        # change to current
        os.chdir(self.cur_dir)
        # capture PYTHONPATH and all variables starting with EASYBUILD
        easybuild_vars = {}
        for name in os.environ:
            if name.startswith("EASYBUILD"):
                easybuild_vars[name] = os.environ[name]

        others = ["PYTHONPATH", "MODULEPATH"]

        for env_var in others:
            if env_var in os.environ:
                easybuild_vars[env_var] = os.environ[env_var]

        for easyconfig in files:
            easybuild_vars['EASYBUILDTESTOUTPUT'] = os.path.join(self.output_dir, "%s.xml" %
                                                                 os.path.basename(easyconfig))
            command = "cd %s && python %s %s" % (self.cur_dir, sys.argv[0], easyconfig)
            self.log.debug("submitting: %s" % command)
            self.log.debug("env vars set: %s" % easybuild_vars)
            job = PbsJob(command, easyconfig, easybuild_vars)
            try:
                job.submit()
                self.jobs.append(job)
            except EasyBuildError, err:
                self.log.warn("Failed to submit job for easyconfig: %s, error: %s" % (easyconfig, err))

    def performStep(self, fase, obj, method):
        """
        Perform method on object if it can be build
        """
        if obj not in self.build_stopped:
            try:
                method(obj)
            except EasyBuildError, err:
                # we cannot continue building it
                self.build_ok = False
                self.test_results.append((obj, fase, err))
                # keep a dict of so we can check in O(1) if objects can still be build
                self.build_stopped[obj] = fase

    def runTest(self):
        """
        Actual test, loop over all the different steps in a build
        """
        # handle parallel build
        if self.parallel:
            # ugly while loop to check if some jobs are stilling running (minimizing job.info() calls)
            done = False
            while not done:
                # we can afford to sleep 5 minutes since we don't expect fast completion
                time.sleep(5 * 60)
                done = True
                for job in self.jobs:
                    if job.info():
                        done = False
                        break

            # all build jobs have finished -> aggregate results
            dom = xml.getDOMImplementation()
            root = dom.createDocument(None, "testsuite", None)
            for job in self.jobs:
                # we set this earlier on (cannot be changed inside job)
                xml_output = job.env_vars['EASYBUILDTESTOUTPUT']
                dom = xml.parse(xml_output)
                children = dom.documentElement.getElementsByTagName("testcase")
                for child in children:
                    root.firstChild.appendChild(child)

            output_file = open(os.path.join(self.cur_dir, "parallel-test.xml"), "w")
            root.writexml(output_file, addindent="\t", newl="\n")
            output_file.close()
            return


        self.log.info("Continuing building other packages")
        base_dir = os.getcwd()
        base_env = copy.deepcopy(os.environ)

        for app in self.apps:
            start_time = time.time()
            # start with a clean slate
            os.chdir(base_dir)
            modifyEnv(os.environ, base_env)

            # create a handler per app so we can capture debug output per application
            handler = logging.FileHandler(os.path.join(self.output_dir, "%s-%s.log" % (app.name(), app.installversion())))
            handler.setFormatter(build_log.formatter)

            app.log.addHandler(handler)

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

            # remove handler
            app.log.removeHandler(handler)

            if app not in self.build_stopped:
                # gather build stats
                build_time = round(time.time() - start_time, 2)

                buildstats = {
                              'build_time': build_time,
                              'platform': platform.platform(),
                              'core_count': systemtools.get_core_count(),
                              'cpu_model': systemtools.get_cpu_model(),
                              'install_size': app.installsize(),
                              'timestamp': int(time.time()),
                              'host': os.uname()[1],
                             }
                self.succes.append((app, buildstats))

        for result in self.test_results:
            self.log.info("%s crashed with an error during fase: %s, error: %s" % result)

        failed = len(self.build_stopped)
        total = len(self.apps)


        self.log.info("%s from %s packages failed to build!" % (failed, total))

        self.log.debug("writing xml output to %s" % self.output_file)
        write_to_xml(self.succes, self.test_results, self.output_file)

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

    def create_succes(name, stats):
        el = create_testcase(name)
        text = "\n".join(["%s=%s" % (key, value) for (key, value) in stats.items()])
        build_stats = root.createCDATASection("\n%s\n" % text)
        system_out = root.createElement("system-out")
        el.appendChild(system_out)
        el.lastChild.appendChild(build_stats)
        return el

    properties = root.createElement("properties")
    version = root.createElement("property")
    version.setAttribute("name", "easybuild-version")
    version.setAttribute("value", str(easybuild.VERBOSE_VERSION))
    properties.appendChild(version)

    time = root.createElement("property")
    time.setAttribute("name", "timestamp")
    time.setAttribute("value", str(datetime.now()))
    properties.appendChild(time)

    root.firstChild.appendChild(properties)

    for (obj, fase, error) in failed:
        # try to pretty print
        try:
            el = create_failure("%s/%s" % (obj.name(), obj.installversion()), fase, error)
        except:
            el = create_failure(obj, fase, error)

        root.firstChild.appendChild(el)

    for (obj, stats) in succes:
        el = create_succes("%s/%s" % (obj.name(), obj.installversion()), stats)
        root.firstChild.appendChild(el)

    output_file = open(filename, "w")
    root.writexml(output_file, addindent="\t", newl="\n")
    output_file.close()


# do not use unittest.main() as it will annoyingly parse command line arguments
suite = unittest.TestLoader().loadTestsFromTestCase(BuildTest)
unittest.TextTestRunner(verbosity=2).run(suite)
