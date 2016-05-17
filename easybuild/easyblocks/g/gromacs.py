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
EasyBuild support for building and installing GROMACS, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
@author: Ward Poelmans (Ghent University)
"""
import glob
import os
import re
from distutils.version import LooseVersion
from vsc.utils.missing import any

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root
from easybuild.tools.systemtools import get_platform_name


class EB_GROMACS(CMakeMake):
    """Support for building/installing GROMACS."""

    def __init__(self, *args, **kwargs):
        """Initialize GROMACS-specific variables."""
        super(EB_GROMACS, self).__init__(*args, **kwargs)
        self.lib_subdir = ''

    def configure_step(self):
        """Custom configuration procedure for GROMACS: set configure options for configure or cmake."""

        if LooseVersion(self.version) < LooseVersion('4.6'):
            self.log.info("Using configure script for configuring GROMACS build.")
            raise EasyBuildError("Configuration procedure for older GROMACS versions not implemented yet.")
        else:
            # build a release build
            self.cfg.update('configopts', "-DCMAKE_BUILD_TYPE=Release")

            # prefer static libraries, if available
            self.cfg.update('configopts', "-DGMX_PREFER_STATIC_LIBS=ON")

            # always specify to use external BLAS/LAPACK
            self.cfg.update('configopts', "-DGMX_EXTERNAL_BLAS=ON -DGMX_EXTERNAL_LAPACK=ON")

            # disable GUI tools
            self.cfg.update('configopts', "-DGMX_X11=OFF")

            # enable OpenMP support if desired
            if self.toolchain.options.get('openmp', None):
                self.cfg.update('configopts', "-DGMX_OPENMP=ON")
            else:
                self.cfg.update('configopts', "-DGMX_OPENMP=OFF")

            # enable MPI support if desired
            if self.toolchain.options.get('usempi', None):
                self.cfg.update('configopts', "-DGMX_MPI=ON -DGMX_THREAD_MPI=OFF")
            else:
                self.cfg.update('configopts', "-DGMX_MPI=OFF")

            # explicitely disable GPU support if CUDA is not available,
            # to avoid that GROMACS find and uses a system-wide CUDA compiler
            cuda = get_software_root('CUDA')
            if cuda:
                self.cfg.update('configopts', "-DGMX_GPU=ON -DCUDA_TOOLKIT_ROOT_DIR=%s" % cuda)
            else:
                self.cfg.update('configopts', "-DGMX_GPU=OFF")

            if get_software_root('imkl'):
                # using MKL for FFT, so it will also be used for BLAS/LAPACK
                self.cfg.update('configopts', '-DGMX_FFT_LIBRARY=mkl -DMKL_INCLUDE_DIR="$EBROOTMKL/mkl/include" ')
                mkl_libs = [os.path.join(os.getenv('LAPACK_LIB_DIR'), lib) for lib in ['libmkl_lapack.a']]
                self.cfg.update('configopts', '-DMKL_LIBRARIES="%s" ' % ';'.join(mkl_libs))
            else:
                for libname in ['BLAS', 'LAPACK']:
                    lib_dir = os.getenv('%s_LIB_DIR' % libname)
                    libs = os.getenv('LIB%s' % libname)
                    self.cfg.update('configopts', '-DGMX_%s_USER="-L%s %s"' % (libname, lib_dir, libs))

            # set regression test path
            prefix = 'regressiontests'
            if any([src['name'].startswith(prefix) for src in self.src]):
                self.cfg.update('configopts', "-DREGRESSIONTEST_PATH='%%(builddir)s/%s-%%(version)s' " % prefix)

        # no more GSL support in GROMACS 5.x, see http://redmine.gromacs.org/issues/1472
        if LooseVersion(self.version) < LooseVersion('5.0'):
            # enable GSL when it's provided
            if get_software_root('GSL'):
                self.cfg.update('configopts', "-DGMX_GSL=ON")
            else:
                self.cfg.update('configopts', "-DGMX_GSL=OFF")

        # complete configuration with configure_method of parent
        out = super(EB_GROMACS, self).configure_step()

        # for recent GROMACS versions, make very sure that a decent BLAS, LAPACK and FFT is found and used
        if LooseVersion(self.version) >= LooseVersion('4.6.5'):
            patterns = [
                r"Using external FFT library - \S*",
                r"Looking for dgemm_ - found",
                r"Looking for cheev_ - found",
            ]
            for pattern in patterns:
                regex = re.compile(pattern, re.M)
                if not regex.search(out):
                    raise EasyBuildError("Pattern '%s' not found in GROMACS configuration output.", pattern)

    def test_step(self):
        """Specify to running tests is done using 'make check'."""
        # allow to escape testing by setting runtest to False
        if not self.cfg['runtest'] and not isinstance(self.cfg['runtest'], bool):
            self.cfg['runtest'] = 'check'

        # make very sure OMP_NUM_THREADS is set to 1, to avoid hanging GROMACS regression test
        env.setvar('OMP_NUM_THREADS', '1')

        super(EB_GROMACS, self).test_step()

    def install_step(self):
        """Custom install step for GROMACS; figure out where libraries were installed to."""
        super(EB_GROMACS, self).install_step()

        # the GROMACS libraries get installed in different locations (deeper subdirectory), depending on the platform;
        # this is determined by the GNUInstallDirs CMake module;
        # rather than trying to replicate the logic, we just figure out where the library was placed

        if LooseVersion(self.version) < LooseVersion('5.0'):
            # libgmx.a or libgmx_mpi.a
            libname = 'libgmx*.a'
        else:
            # libgromacs.a or libgromacs_mpi.a
            libname = 'libgromacs*.a'

        for libdir in ['lib', 'lib64']:
            if os.path.exists(os.path.join(self.installdir, libdir)):
                for subdir in [libdir, os.path.join(libdir, '*')]:
                    libpaths = glob.glob(os.path.join(self.installdir, subdir, libname))
                    if libpaths:
                        self.lib_subdir = os.path.dirname(libpaths[0])[len(self.installdir)+1:]
                        self.log.info("Found lib subdirectory that contains %s: %s", libname, self.lib_subdir)
                        break

        if not self.lib_subdir:
            raise EasyBuildError("Failed to determine lib subdirectory in %s", self.installdir)

    def make_module_req_guess(self):
        """Custom library subdirectories for GROMACS."""
        guesses = super(EB_GROMACS, self).make_module_req_guess()
        guesses.update({
            'LD_LIBRARY_PATH': [self.lib_subdir],
            'LIBRARY_PATH': [self.lib_subdir],
            'PKG_CONFIG_PATH': [os.path.join(self.lib_subdir, 'pkgconfig')],
        })
        return guesses

    def sanity_check_step(self):
        """Custom sanity check for GROMACS."""

        suff = ''
        if self.toolchain.options.get('usempi', None):
            suff = '_mpi'

        # in GROMACS v5.1, only 'gmx' binary is there
        # (only) in GROMACS v5.0, other binaries are symlinks to 'gmx'
        binaries = []
        if LooseVersion(self.version) < LooseVersion('5.1'):
            binaries.extend(['editconf', 'g_lie', 'genbox', 'genconf', 'mdrun'])
        if LooseVersion(self.version) >= LooseVersion('5.0'):
            binaries.append('gmx')

        # check for a handful of binaries/libraries that should be there
        if LooseVersion(self.version) < LooseVersion('5.0'):
            libnames = ['gmxana', 'gmx', 'gmxpreprocess', 'md']
        else:
            libnames = ['gromacs']

        libs = ['lib%s%s.a' % (libname, suff) for libname in libnames]

        custom_paths = {
            'files': ['bin/%s%s' % (binary, suff) for binary in binaries] +
                     [os.path.join(self.lib_subdir, lib) for lib in libs],
            'dirs': ['include/gromacs', os.path.join(self.lib_subdir, 'pkgconfig')]
        }
        super(EB_GROMACS, self).sanity_check_step(custom_paths=custom_paths)
