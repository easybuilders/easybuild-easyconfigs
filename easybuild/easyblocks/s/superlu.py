##
# Copyright 2016 University of Luxembourg
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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
EasyBuild support for building and installing the SuperLU library, implemented as an easyblock

@author: Xavier Besseron (University of Luxembourg)
"""

import os

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.systemtools import get_shared_lib_ext
from easybuild.tools.modules import get_software_root


class EB_SuperLU(CMakeMake):
    """
    Support for building the SuperLU library
    """

    @staticmethod
    def extra_options():
        """
        Define custom easyconfig parameters for SuperLU.
        """
        extra_vars = {
            'build_shared_libs': [False, "Build shared library (instead of static library)", CUSTOM],
        }
        return CMakeMake.extra_options(extra_vars)


    def configure_step(self):
        """
        Set the CMake options for SuperLU
        """
        self.cfg['separate_build_dir'] = True

        if self.cfg['build_shared_libs']:
            self.cfg['configopts'] += "-DBUILD_SHARED_LIBS=ON "
        else:
            self.cfg['configopts'] += "-DBUILD_SHARED_LIBS=OFF "

        # Make sure to add -fPIC
        self.cfg['configopts'] += "-DCMAKE_POSITION_INDEPENDENT_CODE=ON "

        # Make sure not to build the slow BLAS library included in the package
        self.cfg['configopts'] += "-Denable_blaslib=OFF "

        # Set the BLAS library to use
        # For this, use the BLA_VENDOR option from the FindBLAS module of CMake
        # cf https://cmake.org/cmake/help/latest/module/FindBLAS.html
        if get_software_root('IMKL'):
            self.cfg['configopts'] += '-DBLA_VENDOR="Intel10_64lp" '
        elif get_software_root('ACML'):
            self.cfg['configopts'] += '-DBLA_VENDOR="ACML" '
        elif get_software_root('ATLAS'):
            self.cfg['configopts'] += '-DBLA_VENDOR="ATLAS" '
        elif get_software_root('OpenBLAS'):
            # Unfortunately, OpenBLAS is not recognized by FindBLAS from CMake,
            # we have to specify the OpenBLAS library manually
            self.cfg['configopts'] += '-DBLAS_LIBRARIES="${EBROOTOPENBLAS}/lib/libopenblas.a;-pthread" '
        else:
            # Fallback on Generic BLAS otherwise
            self.cfg['configopts'] += '-DBLA_VENDOR="Generic" '

        super(EB_SuperLU, self).configure_step()


    def test_step(self):
        """
        Run the testsuite of SuperLU
        """
        self.cfg['configopts'] = "test"
        super(EB_SuperLU, self).test_step()


    def install_step(self):
        """
        Custom install procedure for SuperLU
        """
        super(EB_SuperLU, self).install_step()

        if self.cfg['build_shared_libs']:
            lib_ext = get_shared_lib_ext()
        else:
            lib_ext = "a"
        expected_libpath = os.path.join(self.installdir, "lib", "libsuperlu.%s" % lib_ext)
        actual_libpath   = os.path.join(self.installdir, "lib", "libsuperlu_%s.%s" % (self.cfg['version'],lib_ext) )

        if not os.path.exists(expected_libpath):
            os.symlink(actual_libpath, expected_libpath)


    def sanity_check_step(self):
        """
        Check for main library files for SuperLU
        """
        if self.cfg['build_shared_libs']:
            lib_ext = get_shared_lib_ext()
        else:
            lib_ext = "a"

        custom_paths = {
            'files': ["include/supermatrix.h", "lib/libsuperlu.%s" % lib_ext],
            'dirs': [],
        }
        super(EB_SuperLU, self).sanity_check_step(custom_paths=custom_paths)
