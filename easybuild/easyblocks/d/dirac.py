##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
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
"""
EasyBuild support for building and installing DIRAC, implemented as an easyblock
"""
import os
import re
import shutil
import tempfile

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.run import run_cmd


class EB_DIRAC(CMakeMake):
    """Support for building/installing DIRAC."""

    def configure_step(self):
        """Custom configuration procedure for DIRAC."""

        # make very sure the install directory isn't there yet, since it may cause problems if it used (forced rebuild)
        if os.path.exists(self.installdir):
            self.log.warning("Found existing install directory %s, removing it to avoid problems", self.installdir)
            try:
                shutil.rmtree(self.installdir)
            except OSError as err:
                raise EasyBuildError("Failed to remove existing install directory %s: %s", self.installdir, err)

        self.cfg['separate_build_dir'] = True
        self.cfg.update('configopts', "-DENABLE_MPI=ON -DCMAKE_BUILD_TYPE=release")

        # complete configuration with configure_method of parent
        super(EB_DIRAC, self).configure_step()

    def test_step(self):
        """Custom built-in test procedure for DIRAC."""
        if self.cfg['runtest']:
            # set up test environment
            # see http://diracprogram.org/doc/release-14/installation/testing.html
            env.setvar('DIRAC_TMPDIR', tempfile.mkdtemp(prefix='dirac-test-'))
            env.setvar('DIRAC_MPI_COMMAND', self.toolchain.mpi_cmd_for('', self.cfg['parallel']))

            # run tests (may take a while, especially if some tests take a while to time out)
            self.log.info("Running tests may take a while, especially if some tests timeout (default timeout is 1500s)")
            cmd = "make test"
            out, ec = run_cmd(cmd, simple=False, log_all=False, log_ok=False)

            # check that majority of tests pass
            # some may fail due to timeout, but that's acceptable
            # cfr. https://groups.google.com/forum/#!msg/dirac-users/zEd5-xflBnY/OQ1pSbuX810J

            # over 90% of tests should pass
            passed_regex = re.compile('^(9|10)[0-9.]+% tests passed', re.M)
            if not passed_regex.search(out) and not self.dry_run:
                raise EasyBuildError("Too many failed tests; '%s' not found in test output: %s",
                                     passed_regex.pattern, out)

            # extract test results
            test_result_regex = re.compile(r'^\s*[0-9]+/[0-9]+ Test \s*#[0-9]+: .*', re.M)
            test_results = test_result_regex.findall(out)
            if test_results:
                self.log.info("Found %d test results: %s", len(test_results), test_results)
            elif self.dry_run:
                # dummy test result
                test_results = ["1/1 Test  #1: dft_alda_xcfun .............................   Passed   72.29 sec"]
            else:
                raise EasyBuildError("Couldn't find *any* test results?")

            test_count_regex = re.compile(r'^\s*[0-9]+/([0-9]+)')
            res = test_count_regex.search(test_results[0])
            if res:
                test_count = int(res.group(1))
            elif self.dry_run:
                # a single dummy test result
                test_count = 1
            else:
                raise EasyBuildError("Failed to determine total test count from %s using regex '%s'",
                                     test_results[0], test_count_regex.pattern)

            if len(test_results) != test_count:
                raise EasyBuildError("Expected to find %s test results, but found %s", test_count, len(test_results))

            # check test results, only 'Passed' or 'Timeout' are acceptable outcomes
            faulty_tests = []
            for test_result in test_results:
                if ' Passed ' not in test_result:
                    self.log.warning("Found failed test: %s", test_result)
                    if '***Timeout' not in test_result:
                        faulty_tests.append(test_result)

            if faulty_tests:
                raise EasyBuildError("Found tests failing due to something else than timeout: %s", faulty_tests)

    def sanity_check_step(self):
        """Custom sanity check for DIRAC."""
        custom_paths = {
            'files': ['bin/pam-dirac'],
            'dirs': ['share/dirac'],
        }
        super(EB_DIRAC, self).sanity_check_step(custom_paths=custom_paths)
