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
EasyBuild support for building and installing TINKER, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
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
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import mkdir
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import DARWIN, LINUX, get_os_type


class EB_TINKER(EasyBlock):
    """Support for building/installing TINKER."""

    def __init__(self, *args, **kwargs):
        """Custom easyblock constructor for TINKER: initialise class variables."""
        super(EB_TINKER, self).__init__(*args, **kwargs)

        self.build_subdir = None
        self.build_in_installdir = True

    def configure_step(self):
        """Custom configuration procedure for TINKER."""
        # make sure FFTW is available
        if get_software_root('FFTW') is None:
            raise EasyBuildError("FFTW dependency is not available.")

        os_dirs = {
            LINUX: 'linux',
            DARWIN: 'macosx',
        }
        os_type = get_os_type()
        os_dir = os_dirs.get(os_type)
        if os_dir is None:
            raise EasyBuildError("Failed to determine OS directory for %s (known: %s)", os_type, os_dirs)

        comp_dirs = {
            toolchain.INTELCOMP: 'intel',
            toolchain.GCC: 'gfortran',
        }
        comp_fam = self.toolchain.comp_family()
        comp_dir = comp_dirs.get(comp_fam)
        if comp_dir is None:
            raise EasyBuildError("Failed to determine compiler directory for %s (known: %s)", comp_fam, comp_dirs)

        self.build_subdir = os.path.join(os_dir, comp_dir)
        self.log.info("Using build scripts from %s subdirectory" % self.build_subdir)

        # patch 'link.make' script to use FFTW provided via EasyBuild
        link_make_fp = os.path.join(self.cfg['start_dir'], self.build_subdir, 'link.make')
        for line in fileinput.input(link_make_fp, inplace=1, backup='.orig'):
            line = re.sub(r"libfftw3_threads.a libfftw3.a", r"-L$EBROOTFFTW/lib -lfftw3_threads -lfftw3", line)
            sys.stdout.write(line)

    def build_step(self):
        """Custom build procedure for TINKER."""
        source_dir = os.path.join(self.cfg['start_dir'], 'source')
        try:
            os.chdir(source_dir)
        except OSError, err:
            raise EasyBuildError("Failed to move to %s: %s", source_dir, err)

        run_cmd(os.path.join(self.cfg['start_dir'], self.build_subdir, 'compile.make'))
        run_cmd(os.path.join(self.cfg['start_dir'], self.build_subdir, 'library.make'))
        run_cmd(os.path.join(self.cfg['start_dir'], self.build_subdir, 'link.make'))

    def test_step(self):
        """Custom built-in test procedure for TINKER."""
        if self.cfg['runtest']:
            # copy tests, params and built binaries to temporary directory for testing
            tmpdir = tempfile.mkdtemp()
            testdir = os.path.join(tmpdir, 'test')

            mkdir(os.path.join(tmpdir, 'bin'))
            binaries = glob.glob(os.path.join(self.cfg['start_dir'], 'source', '*.x'))
            try:
                for binary in binaries:
                    shutil.copy2(binary, os.path.join(tmpdir, 'bin', os.path.basename(binary)[:-2]))
                shutil.copytree(os.path.join(self.cfg['start_dir'], 'test'), testdir)
                shutil.copytree(os.path.join(self.cfg['start_dir'], 'params'), os.path.join(tmpdir, 'params'))
            except OSError, err:
                raise EasyBuildError("Failed to copy binaries and tests to %s: %s", tmpdir, err)

            try:
                os.chdir(testdir)
            except OSError, err:
                raise EasyBuildError("Failed to move to %s to run tests: %s", testdir, err)

            # run all tests via the provided 'run' scripts
            tests = glob.glob(os.path.join(testdir, '*.run'))
            # gpcr takes too logn (~1h), ifabp fails due to input issues (?)
            tests = [t for t in tests if not (t.endswith('gpcr.run') or t.endswith('ifabp.run'))]
            for test in tests:
                run_cmd(test)

    def install_step(self):
        """Custom install procedure for TINKER."""
        source_dir = os.path.join(self.cfg['start_dir'], 'source')
        try:
            os.chdir(source_dir)
        except OSError, err:
            raise EasyBuildError("Failed to move to %s: %s", source_dir, err)

        mkdir(os.path.join(self.cfg['start_dir'], 'bin'))
        run_cmd(os.path.join(self.cfg['start_dir'], self.build_subdir, 'rename.make'))

    def sanity_check_step(self):
        """Custom sanity check for TINKER."""
        custom_paths = {
            'files': ['tinker/source/libtinker.a'],
            'dirs': ['tinker/bin'],
        }
        super(EB_TINKER, self).sanity_check_step(custom_paths=custom_paths)

    def make_module_req_guess(self):
        """Custom guesses for module file prepend-path statements."""
        guesses = super(EB_TINKER, self).make_module_req_guess()
        guesses['PATH'].append(os.path.join('tinker', 'bin'))
        guesses['LIBRARY_PATH'].append(os.path.join('tinker', 'source'))
        return guesses
