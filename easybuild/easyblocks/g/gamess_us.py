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
EasyBuild support for building and installing GAMESS-US, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
@author: Toon Willems (Ghent University)
@author: Pablo Escobar (sciCORE, SIB, University of Basel)
@author: Benjamin Roberts (The University of Auckland)
"""
import fileinput
import glob
import os
import re
import shutil
import sys
import tempfile

import easybuild.tools.toolchain as toolchain
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM, MANDATORY
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir, read_file, write_file
from easybuild.tools.modules import get_software_root, get_software_version
from easybuild.tools.run import run_cmd, run_cmd_qa
from easybuild.tools.systemtools import get_platform_name
from easybuild.tools import toolchain


class EB_GAMESS_minus_US(EasyBlock):
    """Support for building/installing GAMESS-US."""

    @staticmethod
    def extra_options():
        """Define custom easyconfig parameters for GAMESS-US."""
        extra_vars = {
            'ddi_comm': ['mpi', "DDI communication layer to use", CUSTOM],
            'maxcpus': [None, "Maximum number of cores per node", MANDATORY],
            'maxnodes': [None, "Maximum number of nodes", MANDATORY],
            'runtest': [True, "Run GAMESS-US tests", CUSTOM],
            'scratch_dir': ['$TMPDIR', "Scratch dir to be used in rungms script", CUSTOM],
        }
        return EasyBlock.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Easyblock constructor, enable building in installation directory."""
        super(EB_GAMESS_minus_US, self).__init__(*args, **kwargs)
        self.build_in_installdir = True
        self.testdir = None
        if self.cfg['runtest']:
            self.testdir = tempfile.mkdtemp()
            # make sure test dir doesn't contain [ or ], rungms csh script doesn't handle that well ("set: No match")
            if re.search(r'[\[\]]', self.testdir):
                raise EasyBuildError("Temporary dir for tests '%s' will cause problems with rungms csh script", self.testdir)

    def extract_step(self):
        """Extract sources."""
        # strip off 'gamess' part to avoid having everything in a 'gamess' subdirectory
        self.cfg['unpack_options'] = "--strip-components=1"
        super(EB_GAMESS_minus_US, self).extract_step()

    def configure_step(self):
        """Configure GAMESS-US build via provided interactive 'config' script."""

        # machine type
        platform_name = get_platform_name()
        x86_64_linux_re = re.compile('^x86_64-.*$')
        if x86_64_linux_re.match(platform_name):
            machinetype = "linux64"
        else:
            raise EasyBuildError("Build target %s currently unsupported", platform_name)

        # compiler config
        comp_fam = self.toolchain.comp_family()
        fortran_comp, fortran_ver = None, None
        if comp_fam == toolchain.INTELCOMP:
            fortran_comp = 'ifort'
            (out, _) = run_cmd("ifort -v", simple=False)
            res = re.search(r"^ifort version ([0-9]+)\.[0-9.]+$", out)
            if res:
                fortran_ver = res.group(1)
            else:
                raise EasyBuildError("Failed to determine ifort major version number")
        elif comp_fam == toolchain.GCC:
            fortran_comp = 'gfortran'
            fortran_ver = '.'.join(get_software_version('GCC').split('.')[:2])
        else:
            raise EasyBuildError("Compiler family '%s' currently unsupported.", comp_fam)

        # math library config
        known_mathlibs = ['imkl', 'OpenBLAS', 'ATLAS', 'ACML']
        mathlib, mathlib_root = None, None
        for mathlib in known_mathlibs:
            mathlib_root = get_software_root(mathlib)
            if mathlib_root is not None:
                break
        if mathlib_root is None:
            raise EasyBuildError("None of the known math libraries (%s) available, giving up.", known_mathlibs)
        if mathlib == 'imkl':
            mathlib = 'mkl'
            mathlib_root = os.path.join(mathlib_root, 'mkl')
        else:
            mathlib = mathlib.lower()

        # verify selected DDI communication layer
        known_ddi_comms = ['mpi', 'mixed', 'shmem', 'sockets']
        if not self.cfg['ddi_comm'] in known_ddi_comms:
            raise EasyBuildError("Unsupported DDI communication layer specified (known: %s): %s",
                                 known_ddi_comms, self.cfg['ddi_comm'])

        # MPI library config
        mpilib, mpilib_root, mpilib_path = None, None, None
        if self.cfg['ddi_comm'] == 'mpi':

            known_mpilibs = ['impi', 'OpenMPI', 'MVAPICH2', 'MPICH2']
            for mpilib in known_mpilibs:
                mpilib_root = get_software_root(mpilib)
                if mpilib_root is not None:
                    break
            if mpilib_root is None:
                raise EasyBuildError("None of the known MPI libraries (%s) available, giving up.", known_mpilibs)
            mpilib_path = mpilib_root
            if mpilib == 'impi':
                mpilib_path = os.path.join(mpilib_root, 'intel64')
            else:
                mpilib = mpilib.lower()

        # run interactive 'config' script to generate install.info file
        cmd = "%(preconfigopts)s ./config %(configopts)s" % {
            'preconfigopts': self.cfg['preconfigopts'],
            'configopts': self.cfg['configopts'],
        }
        qa = {
            "After the new window is open, please hit <return> to go on.": '',
            "please enter your target machine name: ": machinetype,
            "Version? [00] ": self.version,
            "Please enter your choice of FORTRAN: ": fortran_comp,
            "hit <return> to continue to the math library setup.": '',
            "MKL pathname? ": mathlib_root,
            "MKL version (or 'skip')? ": 'skip',
            "please hit <return> to compile the GAMESS source code activator": '',
            "please hit <return> to set up your network for Linux clusters.": '',
            "communication library ('sockets' or 'mpi')? ": self.cfg['ddi_comm'],
            "Enter MPI library (impi, mvapich2, mpt, sockets):": mpilib,
            "Please enter your %s's location: " % mpilib: mpilib_root,
            "Do you want to try LIBCCHEM?  (yes/no): ": 'no',
            "Enter full path to OpenBLAS libraries (without 'lib' subdirectory):": mathlib_root,
        }
        stdqa = {
            r"GAMESS directory\? \[.*\] ": self.builddir,
            r"GAMESS build directory\? \[.*\] ": self.installdir,  # building in install directory
            r"Enter only the main version number, such as .*\nVersion\? ": fortran_ver,
            r"gfortran version.\nPlease enter only the first decimal place, such as .*:": fortran_ver,
            "Enter your choice of 'mkl' or .* 'none': ": mathlib,
        }
        run_cmd_qa(cmd, qa=qa, std_qa=stdqa, log_all=True, simple=True)

        self.log.debug("Contents of install.info:\n%s" % read_file(os.path.join(self.builddir, 'install.info')))

        # patch hardcoded settings in rungms to use values specified in easyconfig file
        rungms = os.path.join(self.builddir, 'rungms')
        extra_gmspath_lines = "set ERICFMT=$GMSPATH/auxdata/ericfmt.dat\nset MCPPATH=$GMSPATH/auxdata/MCP\n"
        try:
            for line in fileinput.input(rungms, inplace=1, backup='.orig'):
                line = re.sub(r"^(\s*set\s*TARGET)=.*", r"\1=%s" % self.cfg['ddi_comm'], line)
                line = re.sub(r"^(\s*set\s*GMSPATH)=.*", r"\1=%s\n%s" % (self.installdir, extra_gmspath_lines), line)
                line = re.sub(r"(null\) set VERNO)=.*", r"\1=%s" % self.version, line)
                line = re.sub(r"^(\s*set DDI_MPI_CHOICE)=.*", r"\1=%s" % mpilib, line)
                line = re.sub(r"^(\s*set DDI_MPI_ROOT)=.*%s.*" % mpilib.lower(), r"\1=%s" % mpilib_path, line)
                line = re.sub(r"^(\s*set GA_MPI_ROOT)=.*%s.*" % mpilib.lower(), r"\1=%s" % mpilib_path, line)
                # comment out all adjustments to $LD_LIBRARY_PATH that involves hardcoded paths
                line = re.sub(r"^(\s*)(setenv\s*LD_LIBRARY_PATH\s*/.*)", r"\1#\2", line)
                if self.cfg['scratch_dir']:
                    line = re.sub(r"^(\s*set\s*SCR)=.*", r"\1=%s" % self.cfg['scratch_dir'], line)
                    line = re.sub(r"^(\s*set\s*USERSCR)=.*", r"\1=%s" % self.cfg['scratch_dir'], line)
                sys.stdout.write(line)
        except IOError, err:
            raise EasyBuildError("Failed to patch %s: %s", rungms, err)

    def build_step(self):
        """Custom build procedure for GAMESS-US: using compddi, compall and lked scripts."""
        compddi = os.path.join(self.cfg['start_dir'], 'ddi', 'compddi')
        run_cmd(compddi, log_all=True, simple=True)

        # make sure the libddi.a library is present
        libddi = os.path.join(self.cfg['start_dir'], 'ddi', 'libddi.a')
        if not os.path.isfile(libddi):
            raise EasyBuildError("The libddi.a library (%s) was never built", libddi)
        else:
            self.log.info("The libddi.a library (%s) was successfully built." % libddi)

        compall_cmd = os.path.join(self.cfg['start_dir'], 'compall')
        compall = "%s %s %s" % (self.cfg['prebuildopts'], compall_cmd, self.cfg['buildopts'])
        run_cmd(compall, log_all=True, simple=True)

        cmd = "%s gamess %s" % (os.path.join(self.cfg['start_dir'], 'lked'), self.version)
        run_cmd(cmd, log_all=True, simple=True)

    def test_step(self):
        """Run GAMESS-US tests (if 'runtest' easyconfig parameter is set to True)."""
        # don't use provided 'runall' script for tests, since that only runs the tests single-core
        if self.cfg['runtest']:
            try:
                cwd = os.getcwd()
                os.chdir(self.testdir)
            except OSError, err:
                raise EasyBuildError("Failed to move to temporary directory for running tests: %s", err)

            # copy input files for exam<id> standard tests
            for test_input in glob.glob(os.path.join(self.installdir, 'tests', 'standard', 'exam*.inp')):
                try:
                    shutil.copy2(test_input, os.getcwd())
                except OSError, err:
                    raise EasyBuildError("Failed to copy %s to %s: %s", test_input, os.getcwd(), err)

            rungms = os.path.join(self.installdir, 'rungms')
            test_env_vars = ['TMPDIR=%s' % self.testdir]
            if self.toolchain.mpi_family() == toolchain.INTELMPI:
                test_env_vars.extend([
                    'I_MPI_FALLBACK=enable',  # enable fallback in case first fabric fails (see $I_MPI_FABRICS_LIST)
                    'I_MPI_HYDRA_BOOTSTRAP=fork',  # tests are only run locally (2 processes), so no SSH required
                ])

            # run all exam<id> tests, dump output to exam<id>.log
            n_tests = 47
            for i in range(1, n_tests+1):
                test_cmd = ' '.join(test_env_vars + [rungms, 'exam%02d' % i, self.version, '1', '2'])
                (out, _) = run_cmd(test_cmd, log_all=True, simple=False)
                write_file('exam%02d.log' % i, out)

            # verify output of tests
            check_cmd = os.path.join(self.installdir, 'tests', 'standard', 'checktst')
            (out, _) = run_cmd(check_cmd, log_all=True, simple=False)
            success_regex = re.compile("^All %d test results are correct" % n_tests, re.M)
            if success_regex.search(out):
                self.log.info("All tests ran successfully!")
            else:
                raise EasyBuildError("Not all tests ran successfully...")

            # cleanup
            os.chdir(cwd)
            try:
                shutil.rmtree(self.testdir)
            except OSError, err:
                raise EasyBuildError("Failed to remove test directory %s: %s", self.testdir, err)

    def install_step(self):
        """Skip install step, since we're building in the install directory."""
        pass

    def sanity_check_step(self):
        """Custom sanity check for GAMESS-US."""
        custom_paths = {
            'files': ['gamess.%s.x' % self.version, 'rungms'],
            'dirs': [],
        }
        super(EB_GAMESS_minus_US, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_extra(self):
        """Define GAMESS-US specific variables in generated module file, i.e. $GAMESSUSROOT."""
        txt = super(EB_GAMESS_minus_US, self).make_module_extra()
        txt += self.module_generator.set_environment('GAMESSUSROOT', self.installdir)
        txt += self.module_generator.prepend_paths("PATH", [''])
        return txt
