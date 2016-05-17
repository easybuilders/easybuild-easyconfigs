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
EasyBuild support for building and installing WRF, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import os
import re
import sys

from distutils.version import LooseVersion

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.netcdf import set_netcdf_env_vars  # @UnresolvedImport
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import apply_regex_substitutions, patch_perl_script_autoflush
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd, run_cmd_qa


class EB_WRF(EasyBlock):
    """Support for building/installing WRF."""

    def __init__(self, *args, **kwargs):
        """Add extra config options specific to WRF."""
        super(EB_WRF, self).__init__(*args, **kwargs)

        self.build_in_installdir = True
        self.wrfsubdir = None
        self.comp_fam = None

    @staticmethod
    def extra_options():
        extra_vars = {
            'buildtype': [None, "Specify the type of build (serial, smpar (OpenMP), " \
                                "dmpar (MPI), dm+sm (hybrid OpenMP/MPI)).", MANDATORY],
            'rewriteopts': [True, "Replace -O3 with CFLAGS/FFLAGS", CUSTOM],
            'runtest': [True, "Build and run WRF tests", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def configure_step(self):
        """Configure build:
            - set some magic environment variables
            - run configure script
            - adjust configure.wrf file if needed
        """
        # define $NETCDF* for netCDF dependency (used when creating WRF module file)
        set_netcdf_env_vars(self.log)

        # HDF5 (optional) dependency
        hdf5 = get_software_root('HDF5')
        if hdf5:
            # check if this is parallel HDF5
            phdf5_bins = ['h5pcc', 'ph5diff']
            parallel_hdf5 = True
            for f in phdf5_bins:
                if not os.path.exists(os.path.join(hdf5, 'bin', f)):
                    parallel_hdf5 = False
                    break
            if not (hdf5 or parallel_hdf5):
                raise EasyBuildError("Parallel HDF5 module not loaded?")
            else:
                env.setvar('PHDF5', hdf5)
        else:
            self.log.info("HDF5 module not loaded, assuming that's OK...")

        # JasPer dependency check + setting env vars
        jasper = get_software_root('JasPer')
        if jasper:
            jasperlibdir = os.path.join(jasper, "lib")
            env.setvar('JASPERINC', os.path.join(jasper, "include"))
            env.setvar('JASPERLIB', jasperlibdir)

        else:
            if os.getenv('JASPERINC') or os.getenv('JASPERLIB'):
                raise EasyBuildError("JasPer module not loaded, but JASPERINC and/or JASPERLIB still set?")
            else:
                self.log.info("JasPer module not loaded, assuming that's OK...")

        # enable support for large file support in netCDF
        env.setvar('WRFIO_NCD_LARGE_FILE_SUPPORT', '1')

        # patch arch/Config_new.pl script, so that run_cmd_qa receives all output to answer questions
        patch_perl_script_autoflush(os.path.join("arch", "Config_new.pl"))

        # determine build type option to look for
        build_type_option = None
        self.comp_fam = self.toolchain.comp_family()
        if self.comp_fam == toolchain.INTELCOMP:  #@UndefinedVariable
            if LooseVersion(self.version) >= LooseVersion('3.7'):
                build_type_option = "INTEL\ \(ifort\/icc\)"
            else:
                build_type_option = "Linux x86_64 i486 i586 i686, ifort compiler with icc"

        elif self.comp_fam == toolchain.GCC:  #@UndefinedVariable
            if LooseVersion(self.version) >= LooseVersion('3.7'):
                build_type_option = "GNU\ \(gfortran\/gcc\)"
            else:
                build_type_option = "x86_64 Linux, gfortran compiler with gcc"

        else:
            raise EasyBuildError("Don't know how to figure out build type to select.")

        # fetch selected build type (and make sure it makes sense)
        known_build_types = ['serial', 'smpar', 'dmpar', 'dm+sm']
        self.parallel_build_types = ["dmpar", "smpar", "dm+sm"]
        bt = self.cfg['buildtype']

        if not bt in known_build_types:
            raise EasyBuildError("Unknown build type: '%s'. Supported build types: %s", bt, known_build_types)

        # fetch option number based on build type option and selected build type
        if LooseVersion(self.version) >= LooseVersion('3.7'):
            # the two relevant lines in the configure output for WRF 3.8 are:
            #  13. (serial)  14. (smpar)  15. (dmpar)  16. (dm+sm)   INTEL (ifort/icc)
            #  32. (serial)  33. (smpar)  34. (dmpar)  35. (dm+sm)   GNU (gfortran/gcc)
            build_type_question = "\s*(?P<nr>[0-9]+)\.\ \(%s\).*%s" % (bt, build_type_option)
        else:
            # the relevant lines in the configure output for WRF 3.6 are:
            #  13.  Linux x86_64 i486 i586 i686, ifort compiler with icc  (serial)
            #  14.  Linux x86_64 i486 i586 i686, ifort compiler with icc  (smpar)
            #  15.  Linux x86_64 i486 i586 i686, ifort compiler with icc  (dmpar)
            #  16.  Linux x86_64 i486 i586 i686, ifort compiler with icc  (dm+sm)
            #  32.  x86_64 Linux, gfortran compiler with gcc   (serial)
            #  33.  x86_64 Linux, gfortran compiler with gcc   (smpar)
            #  34.  x86_64 Linux, gfortran compiler with gcc   (dmpar)
            #  35.  x86_64 Linux, gfortran compiler with gcc   (dm+sm)
            build_type_question = "\s*(?P<nr>[0-9]+).\s*%s\s*\(%s\)" % (build_type_option, bt)

        # run configure script
        cmd = "./configure"
        qa = {
              # named group in match will be used to construct answer
              "Compile for nesting? (1=basic, 2=preset moves, 3=vortex following) [default 1]:": "1",
              "Compile for nesting? (0=no nesting, 1=basic, 2=preset moves, 3=vortex following) [default 0]:": "0"
             }
        no_qa = [
                 "testing for fseeko and fseeko64",
                 r"If you wish to change the default options, edit the file:[\s\n]*arch/configure_new.defaults"
                ]
        std_qa = {
                  # named group in match will be used to construct answer
                  r"%s.*\n(.*\n)*Enter selection\s*\[[0-9]+-[0-9]+\]\s*:" % build_type_question: "%(nr)s",
                 }

        run_cmd_qa(cmd, qa, no_qa=no_qa, std_qa=std_qa, log_all=True, simple=True)

        cfgfile = 'configure.wrf'

        # make sure correct compilers are being used
        comps = {
                 'SCC': os.getenv('CC'),
                 'SFC': os.getenv('F90'),
                 'CCOMP': os.getenv('CC'),
                 'DM_FC': os.getenv('MPIF90'),
                 'DM_CC': "%s -DMPI2_SUPPORT" % os.getenv('MPICC'),
                }
        regex_subs = [(r"^(%s\s*=\s*).*$" % k, r"\1 %s" % v) for (k, v) in comps.items()]
        apply_regex_substitutions(cfgfile, regex_subs)

        # rewrite optimization options if desired
        if self.cfg['rewriteopts']:

            # replace default -O3 option in configure.wrf with CFLAGS/FFLAGS from environment
            self.log.info("Rewriting optimization options in %s" % cfgfile)

            # set extra flags for Intel compilers
            # see http://software.intel.com/en-us/forums/showthread.php?t=72109&p=1#146748
            if self.comp_fam == toolchain.INTELCOMP:  #@UndefinedVariable

                # -O3 -heap-arrays is required to resolve compilation error
                for envvar in ['CFLAGS', 'FFLAGS']:
                    val = os.getenv(envvar)
                    if '-O3' in val:
                        env.setvar(envvar, '%s -heap-arrays' % val)
                        self.log.info("Updated %s to '%s'" % (envvar, os.getenv(envvar)))

            # replace -O3 with desired optimization options
            regex_subs = [
                (r"^(FCOPTIM.*)(\s-O3)(\s.*)$", r"\1 %s \3" % os.getenv('FFLAGS')),
                (r"^(CFLAGS_LOCAL.*)(\s-O3)(\s.*)$", r"\1 %s \3" % os.getenv('CFLAGS')),
            ]
            apply_regex_substitutions(cfgfile, regex_subs)

    def build_step(self):
        """Build and install WRF and testcases using provided compile script."""

        # enable parallel build
        p = self.cfg['parallel']
        self.par = ""
        if p:
            self.par = "-j %s" % p

        # build wrf (compile script uses /bin/csh )
        cmd = "tcsh ./compile %s wrf" % self.par
        run_cmd(cmd, log_all=True, simple=True, log_output=True)

        # build two testcases to produce ideal.exe and real.exe
        for test in ["em_real", "em_b_wave"]:
            cmd = "tcsh ./compile %s %s" % (self.par, test)
            run_cmd(cmd, log_all=True, simple=True, log_output=True)

    def test_step(self):
        """Build and run tests included in the WRF distribution."""
        if self.cfg['runtest']:

            # get list of WRF test cases
            self.testcases = []
            if os.path.exists('test'):
                self.testcases = os.listdir('test')

            elif not self.dry_run:
                raise EasyBuildError("Test directory not found, failed to determine list of test cases")

            # exclude 2d testcases in non-parallel WRF builds
            if self.cfg['buildtype'] in self.parallel_build_types:
                self.testcases = [test for test in self.testcases if not "2d_" in test]

            # exclude real testcases
            self.testcases = [test for test in self.testcases if not test.endswith("_real")]

            self.log.debug("intermediate list of testcases: %s" % self.testcases)

            # exclude tests that should not be run
            for test in ["em_esmf_exp", "em_scm_xy", "nmm_tropical_cyclone"]:
                if test in self.testcases:
                    self.testcases.remove(test)

            # some tests hang when WRF is built with Intel compilers
            if self.comp_fam == toolchain.INTELCOMP:  #@UndefinedVariable
                for test in ["em_heldsuarez"]:
                    if test in self.testcases:
                        self.testcases.remove(test)

            # determine parallel setting (1/2 of available processors + 1)
            n = self.cfg['parallel'] / 2 + 1

            # prepare run command

            # stack limit needs to be set to unlimited for WRF to work well
            if self.cfg['buildtype'] in self.parallel_build_types:
                test_cmd = "ulimit -s unlimited && %s && %s" % (self.toolchain.mpi_cmd_for("./ideal.exe", 1),
                                                                self.toolchain.mpi_cmd_for("./wrf.exe", n))
            else:
                test_cmd = "ulimit -s unlimited && ./ideal.exe && ./wrf.exe" % n

            def run_test():
                """Run a single test and check for success."""

                # regex to check for successful test run
                re_success = re.compile("SUCCESS COMPLETE WRF")

                # run test
                run_cmd(test_cmd, log_all=True, simple=True)

                # check for success
                fn = "rsl.error.0000"
                try:
                    f = open(fn, "r")
                    txt = f.read()
                    f.close()
                except IOError, err:
                    raise EasyBuildError("Failed to read output file %s: %s", fn, err)

                if re_success.search(txt):
                    self.log.info("Test %s ran successfully." % test)

                else:
                    raise EasyBuildError("Test %s failed, pattern '%s' not found.", test, re_success.pattern)

                # clean up stuff that gets in the way
                fn_prefs = ["wrfinput_", "namelist.output", "wrfout_", "rsl.out.", "rsl.error."]
                for f in os.listdir('.'):
                    for p in fn_prefs:
                        if f.startswith(p):
                            os.remove(f)
                            self.log.debug("Cleaned up file %s." % f)

            # build an run each test case individually
            for test in self.testcases:

                self.log.debug("Building and running test %s" % test)

                #build_and_install
                cmd = "tcsh ./compile %s %s" % (self.par, test)
                run_cmd(cmd, log_all=True, simple=True)

                # run test
                try:
                    os.chdir('run')

                    if test in ["em_fire"]:

                        # handle tests with subtests seperately
                        testdir = os.path.join("..", "test", test)

                        for subtest in [x for x in os.listdir(testdir) if os.path.isdir(x)]:

                            subtestdir = os.path.join(testdir, subtest)

                            # link required files
                            for f in os.listdir(subtestdir):
                                if os.path.exists(f):
                                    os.remove(f)
                                os.symlink(os.path.join(subtestdir, f), f)

                            # run test
                            run_test()

                    else:

                        # run test
                        run_test()

                    os.chdir('..')

                except OSError, err:
                    raise EasyBuildError("An error occured when running test %s: %s", test, err)

    # building/installing is done in build_step, so we can run tests
    def install_step(self):
        """Building was done in install dir, so nothing to do in install_step."""
        pass

    def sanity_check_step(self):
        """Custom sanity check for WRF."""

        mainver = self.version.split('.')[0]
        self.wrfsubdir = "WRFV%s" % mainver

        files = ['libwrflib.a', 'wrf.exe', 'ideal.exe', 'real.exe', 'ndown.exe', 'tc.exe']
        # nup.exe was 'temporarily removed' in WRF v3.7, at least until 3.8
        if LooseVersion(self.version) < LooseVersion('3.7'):
            files.append('nup.exe')

        custom_paths = {
            'files': [os.path.join(self.wrfsubdir, 'main', f) for f in files],
            'dirs': [os.path.join(self.wrfsubdir, d) for d in ['main', 'run']],
        }

        super(EB_WRF, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):

        mainver = self.version.split('.')[0]
        self.wrfsubdir = "WRFV%s"%mainver

        maindir = os.path.join(self.wrfsubdir, "main")

        return {
                'PATH': [maindir],
                'LD_LIBRARY_PATH': [maindir],
                'MANPATH': [],
               }

    def make_module_extra(self):
        """Add netCDF environment variables to module file."""
        txt = super(EB_WRF, self).make_module_extra()
        for netcdf_var in ['NETCDF', 'NETCDFF']:
            if os.getenv(netcdf_var) is not None:
                txt += self.module_generator.set_environment(netcdf_var, os.getenv(netcdf_var))
        return txt
