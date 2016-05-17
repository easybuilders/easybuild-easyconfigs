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
EasyBuild support for building and installing WIEN2k, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Michael Sluydts (Ghent University)

"""
import fileinput
import os
import re
import shutil
import sys
import tempfile
from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import extract_file, mkdir, read_file, rmtree2, write_file
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd, run_cmd_qa


class EB_WIEN2k(EasyBlock):
    """Support for building/installing WIEN2k."""

    def __init__(self,*args,**kwargs):
        """Enable building in install dir."""
        super(EB_WIEN2k, self).__init__(*args, **kwargs)
        self.build_in_installdir = True

    @staticmethod
    def extra_options():
        testdata_urls = ["http://www.wien2k.at/reg_user/benchmark/test_case.tar.gz",
                         "http://www.wien2k.at/reg_user/benchmark/mpi-benchmark.tar.gz"]

        extra_vars = {
            'runtest': [True, "Run WIEN2k tests", CUSTOM],
            'testdata': [testdata_urls, "test data URL for WIEN2k benchmark test", CUSTOM],
            'wien_mpirun': [None, "MPI wrapper command to use", CUSTOM],
            'remote': [None, "Remote command to use (e.g. pbsssh, ...)", CUSTOM],
            'use_remote': [True, "Whether to remotely login to initiate the k-point parallellization calls", CUSTOM],
            'mpi_remote': [False, "Whether to initiate MPI calls locally or remotely", CUSTOM],
            'wien_granularity': [True, "Granularity for parallel execution (see manual)", CUSTOM],
            'taskset': [None, "Specifies an optional command for binding a process to a specific core", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def extract_step(self):
        """Unpack WIEN2k sources using gunzip and provided expand_lapw script."""
        super(EB_WIEN2k, self).extract_step()

        cmd = "gunzip *gz"
        run_cmd(cmd, log_all=True, simple=True)

        cmd = "./expand_lapw"
        qanda = {'continue (y/n)': 'y'}
        no_qa = [
                 'tar -xf.*',
                 '.*copied and linked.*',
                 ]

        run_cmd_qa(cmd, qanda, no_qa=no_qa, log_all=True, simple=True)

    def configure_step(self):
        """Configure WIEN2k build by patching siteconfig_lapw script and running it."""

        self.cfgscript = "siteconfig_lapw"

        # patch config file first

        # toolchain-dependent values
        comp_answer = None
        if self.toolchain.comp_family() == toolchain.INTELCOMP:  #@UndefinedVariable
            if LooseVersion(get_software_version("icc")) >= LooseVersion("2011"):
                comp_answer = 'I'  # Linux (Intel ifort 12.0 compiler + mkl )
            else:
                comp_answer = "K1"  # Linux (Intel ifort 11.1 compiler + mkl )

        elif self.toolchain.comp_family() == toolchain.GCC:  #@UndefinedVariable
            comp_answer = 'V'  # Linux (gfortran compiler + gotolib)

        else:
            raise EasyBuildError("Failed to determine toolchain-dependent answers.")

        # libraries
        rlibs = "%s %s" % (os.getenv('LIBLAPACK_MT'), self.toolchain.get_flag('openmp'))
        rplibs = [os.getenv('LIBSCALAPACK_MT'), os.getenv('LIBLAPACK_MT')]
        fftwver = get_software_version('FFTW')
        if fftwver:
            suff = ''
            if LooseVersion(fftwver) >= LooseVersion("3"):
                suff = '3'
            rplibs.insert(0, "-lfftw%(suff)s_mpi -lfftw%(suff)s" % {'suff': suff})
        else:
            rplibs.append(os.getenv('LIBFFT'))

        rplibs = ' '.join(rplibs)

        d = {
             'FC': '%s %s' % (os.getenv('F90'), os.getenv('FFLAGS')),
             'MPF': "%s %s" % (os.getenv('MPIF90'), os.getenv('FFLAGS')),
             'CC': os.getenv('CC'),
             'LDFLAGS': '$(FOPT) %s ' % os.getenv('LDFLAGS'),
             'R_LIBS': rlibs,  # libraries for 'real' (not 'complex') binary
             'RP_LIBS' : rplibs,  # libraries for 'real' parallel binary
             'MPIRUN': '',
            }

        for line in fileinput.input(self.cfgscript, inplace=1, backup='.orig'):
            # set config parameters
            for (k,v) in d.items():
                regexp = re.compile('^([a-z0-9]+):%s:.*' % k)
                res = regexp.search(line)
                if res:
                    # we need to exclude the lines with 'current', otherwise we break the script
                    if not res.group(1) == "current":
                        line = regexp.sub('\\1:%s:%s' % (k, v), line)
            # avoid exit code > 0 at end of configuration
            line = re.sub('(\s+)exit 1', '\\1exit 0', line)
            sys.stdout.write(line)

        # set correct compilers
        env.setvar('bin', os.getcwd())

        dc = {
            'COMPILERC': os.getenv('CC'),
            'COMPILER': os.getenv('F90'),
            'COMPILERP': os.getenv('MPIF90'),
        }

        for (k, v) in dc.items():
            write_file(k, v)

        # configure with patched configure script
        self.log.debug('%s part I (configure)' % self.cfgscript)

        cmd = "./%s" % self.cfgscript
        qanda = {
             'Press RETURN to continue': '',
             'Your compiler:': '',
             'Hit Enter to continue': '',
             'Remote shell (default is ssh) =': '',
             'and you need to know details about your installed  mpi ..) (y/n)': 'y',
             'Q to quit Selection:': 'Q',
             'A Compile all programs (suggested) Q Quit Selection:': 'Q',
             ' Please enter the full path of the perl program: ': '',
             'continue or stop (c/s)': 'c',
             '(like taskset -c). Enter N / your_specific_command:': 'N',
        }
        if LooseVersion(self.version) >= LooseVersion("13"):
            fftw_root = get_software_root('FFTW')
            if fftw_root:
                fftw_maj = get_software_version('FFTW').split('.')[0]
                fftw_spec = 'FFTW%s' % fftw_maj
            else:
                raise EasyBuildError("Required FFTW dependency is missing")
            qanda.update({
                 '(not updated) Selection:': comp_answer,
                 'Shared Memory Architecture? (y/N):': 'N',
                 'Set MPI_REMOTE to  0 / 1:': '0',
                 'You need to KNOW details about your installed  MPI and FFTW ) (y/n)': 'y',
                 'Please specify whether you want to use FFTW3 (default) or FFTW2  (FFTW3 / FFTW2):' : fftw_spec,
                 'Please specify the ROOT-path of your FFTW installation (like /opt/fftw3):' : fftw_root,
                 'is this correct? enter Y (default) or n:' : 'Y',
            })
        else:
            qanda.update({
                 'compiler) Selection:': comp_answer,
                 'Shared Memory Architecture? (y/n):': 'n',
                 'If you are using mpi2 set MPI_REMOTE to 0  Set MPI_REMOTE to 0 / 1:': '0',
                 'Do you have MPI and Scalapack installed and intend to run ' \
                    'finegrained parallel? (This is usefull only for BIG cases ' \
                    '(50 atoms and more / unit cell) and you need to know details ' \
                    'about your installed  mpi and fftw ) (y/n)': 'y',
            })

        no_qa = [
            'You have the following mkl libraries in %s :' % os.getenv('MKLROOT'),
            "%s[ \t]*.*" % os.getenv('MPIF90'),
            "%s[ \t]*.*" % os.getenv('F90'),
            "%s[ \t]*.*" % os.getenv('CC'),
            ".*SRC_.*",
            "Please enter the full path of the perl program:",
        ]

        std_qa = {
            r'S\s+Save and Quit[\s\n]+To change an item select option.[\s\n]+Selection:': 'S',
            'Recommended setting for parallel f90 compiler: .* Current selection: Your compiler:': os.getenv('MPIF90'),
        }

        run_cmd_qa(cmd, qanda, no_qa=no_qa, std_qa=std_qa, log_all=True, simple=True)

        # post-configure patches
        parallel_options = {}
        parallel_options_fp = os.path.join(self.cfg['start_dir'], 'parallel_options')

        if self.cfg['wien_mpirun']:
            parallel_options.update({'WIEN_MPIRUN': self.cfg['wien_mpirun']})

        if self.cfg['taskset'] is None:
            self.cfg['taskset'] = 'no'
        parallel_options.update({'TASKSET': self.cfg['taskset']})

        for opt in ['use_remote', 'mpi_remote', 'wien_granularity']:
            parallel_options.update({opt.upper(): int(self.cfg[opt])})

        write_file(parallel_options_fp, '\n'.join(['setenv %s "%s"' % tup for tup in parallel_options.items()]))

        if self.cfg['remote']:
            if self.cfg['remote'] == 'pbsssh':
                extratxt = '\n'.join([
                    '',
                    "set remote = pbsssh",
                    "setenv PBSSSHENV 'LD_LIBRARY_PATH PATH'",
                    '',
                ])
                write_file(parallel_options_fp, extratxt, append=True)
            else:
                raise EasyBuildError("Don't know how to handle remote %s", self.cfg['remote'])

        self.log.debug("Patched file %s: %s", parallel_options_fp, read_file(parallel_options_fp))

    def build_step(self):
        """Build WIEN2k by running siteconfig_lapw script again."""

        self.log.debug('%s part II (build_step)' % self.cfgscript)

        cmd = "./%s" % self.cfgscript

        qanda = {
                 'L Perl path (if not in /usr/bin/perl) Q Quit Selection:': 'R',
                 'A Compile all programs S Select program Q Quit Selection:': 'A',
                 'Press RETURN to continue': '\nQ',  # also answer on first qanda pattern with 'Q' to quit
                 ' Please enter the full path of the perl program: ':'',
                }
        no_qa = [
                 "%s[ \t]*.*" % os.getenv('MPIF90'),
                 "%s[ \t]*.*" % os.getenv('F90'),
                 "%s[ \t]*.*" % os.getenv('CC'),
                 "mv[ \t]*.*",
                 ".*SRC_.*",
                 ".*: warning .*",
                 ".*Stop.",
                 "Compile time errors (if any) were:",
                 "Please enter the full path of the perl program:",
                ]

        self.log.debug("no_qa for %s: %s" % (cmd, no_qa))
        run_cmd_qa(cmd, qanda, no_qa=no_qa, log_all=True, simple=True)

    def test_step(self):
        """Run WIEN2k test benchmarks. """

        def run_wien2k_test(cmd_arg):
            """Run a WPS command, and check for success."""

            cmd = "x_lapw lapw1 %s" % cmd_arg
            (out, _) = run_cmd(cmd, log_all=True, simple=False)

            re_success = re.compile("LAPW1\s+END")
            if not re_success.search(out):
                raise EasyBuildError("Test '%s' in %s failed (pattern '%s' not found)?",
                                     cmd, os.getcwd(), re_success.pattern)
            else:
                self.log.info("Test '%s' seems to have run successfully: %s" % (cmd, out))

        if self.cfg['runtest']:
            if not self.cfg['testdata']:
                raise EasyBuildError("List of URLs for testdata not provided.")

            # prepend $PATH with install directory, define $SCRATCH which is used by the tests
            env.setvar('PATH', "%s:%s" % (self.installdir, os.environ['PATH']))
            try:
                cwd = os.getcwd()

                # create temporary directory
                tmpdir = tempfile.mkdtemp()
                os.chdir(tmpdir)
                self.log.info("Running tests in %s" % tmpdir)

                scratch = os.path.join(tmpdir, 'scratch')
                mkdir(scratch)
                env.setvar('SCRATCH', scratch)

                # download data
                testdata_paths = {}
                for testdata in self.cfg['testdata']:
                    td_path = self.obtain_file(testdata)
                    if not td_path:
                        raise EasyBuildError("Downloading file from %s failed?", testdata)
                    testdata_paths.update({os.path.basename(testdata): td_path})

                self.log.debug('testdata_paths: %s' % testdata_paths)

                # unpack serial benchmark
                serial_test_name = "test_case"
                extract_file(testdata_paths['%s.tar.gz' % serial_test_name], tmpdir)

                # run serial benchmark
                os.chdir(os.path.join(tmpdir, serial_test_name))
                run_wien2k_test("-c")

                # unpack parallel benchmark (in serial benchmark dir)
                parallel_test_name = "mpi-benchmark"
                extract_file(testdata_paths['%s.tar.gz' % parallel_test_name], tmpdir)

                # run parallel benchmark
                os.chdir(os.path.join(tmpdir, serial_test_name))
                run_wien2k_test("-p")

                os.chdir(cwd)
                rmtree2(tmpdir)

            except OSError, err:
                raise EasyBuildError("Failed to run WIEN2k benchmark tests: %s", err)

            self.log.debug("Current dir: %s" % os.getcwd())

    def test_cases_step(self):
        """Run test cases, if specified."""

        for test in self.cfg['tests']:

            # check expected format
            if not len(test) == 4:
                raise EasyBuildError("WIEN2k test case not specified in expected format: "
                                     "(testcase_name, init_lapw_args, run_lapw_args, [scf_regexp_pattern])")
            test_name = test[0]
            init_args = test[1]
            run_args = test[2]
            scf_regexp_patterns = test[3]

            try:
                cwd = os.getcwd()
                # WIEN2k enforces that working dir has same name as test case
                tmpdir = os.path.join(tempfile.mkdtemp(), test_name)

                scratch = os.path.join(tmpdir, 'scratch')
                mkdir(scratch, parents=True)
                env.setvar('SCRATCH', scratch)

                os.chdir(tmpdir)
                self.log.info("Running test case %s in %s" % (test_name, tmpdir))
            except OSError, err:
                raise EasyBuildError("Failed to create temporary directory for test %s: %s", test_name, err)

            # try and find struct file for test
            test_fp = self.obtain_file("%s.struct" % test_name)

            try:
                shutil.copy2(test_fp, tmpdir)
            except OSError, err:
                raise EasyBuildError("Failed to copy %s: %s", test_fp, err)

            # run test
            cmd = "init_lapw %s" % init_args
            run_cmd(cmd, log_all=True, simple=True)

            cmd = "run_lapw %s" % run_args
            run_cmd(cmd, log_all=True, simple=True)

            # check output
            scf_fn = "%s.scf" % test_name
            self.log.debug("Checking output of test %s in %s" % (str(test), scf_fn))
            scftxt = read_file(scf_fn)
            for regexp_pat in scf_regexp_patterns:
                regexp = re.compile(regexp_pat, re.M)
                if not regexp.search(scftxt):
                    raise EasyBuildError("Failed to find pattern %s in %s", regexp.pattern, scf_fn)
                else:
                    self.log.debug("Found pattern %s in %s" % (regexp.pattern, scf_fn))

            # cleanup
            try:
                os.chdir(cwd)
                rmtree2(tmpdir)
            except OSError, err:
                raise EasyBuildError("Failed to clean up temporary test dir: %s", err)

    def install_step(self):
        """Fix broken symlinks after build/installation."""
        # fix broken symlink
        os.remove(os.path.join(self.installdir, "SRC_w2web", "htdocs", "usersguide"))
        os.symlink(os.path.join(self.installdir, "SRC_usersguide_html"),
                   os.path.join(self.installdir, "SRC_w2web","htdocs", "usersguide"))

    def sanity_check_step(self):
        """Custom sanity check for WIEN2k."""

        lapwfiles = []
        for suffix in ['0', '0_mpi', '1', '1_mpi', '1c', '1c_mpi', '2', '2_mpi', '2c' ,'2c_mpi',
                       '3', '3c', '5', '5c', '7', '7c', 'dm', 'dmc', 'so']:
            p = os.path.join(self.installdir, "lapw%s" % suffix)
            lapwfiles.append(p)

        custom_paths = {
            'files': lapwfiles,
            'dirs': [],
        }

        super(EB_WIEN2k, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Set WIENROOT environment variable, and correctly prepend PATH."""

        txt = super(EB_WIEN2k, self).make_module_extra()

        txt += self.module_generator.set_environment("WIENROOT", self.installdir)
        txt += self.module_generator.prepend_paths("PATH", [""])

        return txt
