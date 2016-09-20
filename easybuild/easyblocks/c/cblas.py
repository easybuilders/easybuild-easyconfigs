##
# Copyright 2013 Ghent University
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
EasyBuild support for building and installing CBLAS, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""

import glob
import os
import shutil

from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.tools.build_log import EasyBuildError


class EB_CBLAS(ConfigureMake):
    """
    Support for building CBLAS (BLAS C interface),
    inspired by instructions to build CBLAS for ACML, see https://wiki.fysik.dtu.dk/gpaw/install/Linux/vsc.univie.html
    """

    def configure_step(self):
        """
        Configure CBLAS build by copying Makefile.LINUX to Makefile.in, and setting make options
        """
        try:
            shutil.copy2('Makefile.LINUX', 'Makefile.in')
        except OSError, err:
            raise EasyBuildError("Failed to copy makefile: %s", err)

        if not self.cfg['buildopts']:
            self.cfg.update('buildopts', 'all')

        self.cfg.update('buildopts', 'CC="%s"' % os.getenv('CC'))
        self.cfg.update('buildopts', 'FC="%s"' % os.getenv('F77'))
        self.cfg.update('buildopts', 'CFLAGS="%s -DADD_"' % os.getenv('CFLAGS'))
        self.cfg.update('buildopts', 'FFLAGS="%s -DADD_"' % os.getenv('FFLAGS'))
        blas_lib_dir = os.getenv('BLAS_LIB_DIR')
        blas_libs = [os.path.join(blas_lib_dir, lib) for lib in os.getenv('BLAS_STATIC_LIBS').split(',')]
        self.cfg.update('buildopts', 'BLLIB="%s"' % ' '.join(blas_libs))

    # default build procedure should do

    def install_step(self):
        """
        Install CBLAS: copy libraries to install path.
        """
        srcdir = os.path.join(self.cfg['start_dir'], 'lib')
        targetdir = os.path.join(self.installdir, 'lib')
        try:
            os.makedirs(targetdir)

            shutil.copy2(os.path.join(srcdir, 'cblas_LINUX.a'), os.path.join(targetdir, 'libcblas.a'))
            srclib = os.path.join(srcdir, 'libcblas.so')
            if os.path.exists(srclib):
                for solib in glob.glob(os.path.join(srcdir, 'libcblas.so*')):
                    shutil.copy2(solib, targetdir)
        except OSError, err:
            raise EasyBuildError("Failed to install CBLAS (srcdir: %s, targetdir: %s): %s", srcdir, targetdir, err)

    def sanity_check_step(self):
        """
        Custom sanity check for CBLAS.
        """
        custom_paths = {
                        'files': ["lib/libcblas.a"],
                        'dirs': [],
                       }

        super(EB_CBLAS, self).sanity_check_step(custom_paths=custom_paths)
