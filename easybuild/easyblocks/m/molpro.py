##
# Copyright 2015-2015 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
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
EasyBuild support for Molpro, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import read_file
from easybuild.tools.run import run_cmd


class EB_Molpro(ConfigureMake):
    """Support for building and installing Molpro."""

    def configure_step(self):
        """Custom configuration procedure for Molpro: use 'configure -batch'."""

        self.cfg.update('configopts', "-prefix %s" % self.installdir)

        # compilers
        self.cfg.update('configopts', "-%s -%s" % (os.environ['CC'], os.environ['F90']))

        # MPI
        if self.toolchain.options.get('usempi', None):
            if 'MPI_INC_DIR' in os.environ:
                self.cfg.update('configopts', "-mpp -mppbase %s" % os.environ['MPI_INC_DIR'])
            else:
                raise EasyBuildError("$MPI_INC_DIR not defined")

        # BLAS/LAPACK
        if 'BLAS_LIB_DIR' in os.environ:
            self.cfg.update('configopts', "-blas3 -blaspath %s" % os.environ['BLAS_LIB_DIR'])
        else:
            raise EasyBuildError("$BLAS_LIB_DIR not defined")

        if 'LAPACK_LIB_DIR' in os.environ:
            self.cfg.update('configopts', "-lapack -lapackpath %s" % os.environ['LAPACK_LIB_DIR'])
        else:
            raise EasyBuildError("$LAPACK_LIB_DIR not defined")

        # 32 vs 64 bit
        if self.toolchain.options.get('32bit', None):
            self.cfg.update('configopts', '-i4')
        else:
            self.cfg.update('configopts', '-i8')

        run_cmd("./configure -batch %s" % self.cfg['configopts'])

        self.log.info("Contents of CONFIG file:\n%s", read_file('CONFIG'))

    def build_step(self):
        """
        Custom install procedure for Molpro:
        * put license token in place in $installdir/.token
        * run 'make tuning'
        * install with 'make install'
        """
        if not self.cfg['license_file'] or not os.path.exists(self.cfg['license_file']):
            raise EasyBuildError("Path to an existing license file must be specified in 'license_file' parameter.")

        try:
            shutil.copy2(self.cfg['license_file'], os.path.join(self.installdir, '.token'))

        except OSError as err:
            raise EasyBuildError("Failed to copy license file to install dir: %s", err)

        run_cmd("make tuning")

        super(EB_Molpro, self).install_step()

    def test_step(self):
        """Custom test procedure for Molpro: make quicktest, make test."""
        # check 'main routes' only
        run_cmd("make quicktest")

        # extensive test
        run_cmd("make MOLPRO OPTIONS=-n%s test" % self.cfg['parallel'])

    def sanity_check_step(self):
        """Custom sanity check for Molpro."""
        custom_paths = {
            'files': ['bin/molpro', 'bin/molpros', 'bin/molprop', '.token'],
            'dirs': ['doc', 'examples'],
        }
        super(EB_Molpro, self).sanity_check_step(custom_paths=custom_paths)
