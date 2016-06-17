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
@author: Luca Marsella (CSCS)
@author: Guilherme Peretti-Pezzi (CSCS)
"""
import glob
import os
import re
from distutils.version import LooseVersion
from vsc.utils.missing import any

import easybuild.tools.environment as env
import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import download_file, extract_file
from easybuild.tools.modules import get_software_root
from easybuild.tools.run import run_cmd
from easybuild.tools.systemtools import get_platform_name , get_shared_lib_ext


class EB_GROMACS(CMakeMake):
    """Support for building/installing GROMACS."""

    @staticmethod
    def extra_options():
        extra_vars = {
            'mpisuffix': ['_mpi', "Suffix to append to MPI-enabled executables", CUSTOM],
            'mpiexec': ['mpirun', "MPI executable to use when running tests", CUSTOM],
            'mpiexec_numproc_flag': ['-np', "Flag to introduce the number of MPI tasks when running tests", CUSTOM],
            'mpi_numprocs': [0, "Number of MPI tasks to use when running tests", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def __init__(self, *args, **kwargs):
        """Initialize GROMACS-specific variables."""
        super(EB_GROMACS, self).__init__(*args, **kwargs)
        self.lib_subdir = ''
        self.cmake_objdir_normal = ''
        self.cmake_objdir_mdrun = ''

    def configure_step(self):
        """Custom configuration procedure for GROMACS: set configure options for configure or cmake."""

        if LooseVersion(self.version) < LooseVersion('4.6'):
            self.log.info("Using configure script for configuring GROMACS build.")
            # Use static libraries if possible
            self.cfg.update('configopts', "--enable-static")

            # Use external BLAS and LAPACK
            self.cfg.update('configopts', "--with-external-blas --with-external-lapack")
            self.cfg.update("preconfigopts", 'LIBS="${EBVARLIBLAPACK} ${LIBS}"')

            # Don't use the X window system
            self.cfg.update('configopts', "--without-x")

            # OpenMP is not supported for versions older than 4.5.
            if LooseVersion(self.version) >= LooseVersion('4.5'):
                # enable OpenMP support if desired
                if self.toolchain.options.get('openmp', None):
                    self.cfg.update('configopts', "--enable-threads")
                else:
                    self.cfg.update('configopts', "--disable-threads")
            elif self.toolchain.options.get('openmp', None):
                raise EasyBuildError("GROMACS version {0} does not support OpenMP.".format(LooseVersion(self.version)))

            # GSL support
            if get_software_root('GSL'):
                self.cfg.update('configopts', "--with-gsl")
            else:
                self.cfg.update('configopts', "--without-gsl")

            # I don't think it's necessary to explicitly set the location
            # of math libraries (MKL and/or BLAS, LAPACK) but we shall see.

            # Because ConfigureMake is (currently) an ancestral class of
            # CMakeMake, we may not need to specify it as an ancestral class
            # of gromacs.py.
            ConfigureMake.configure_step(self)
        else:
            # build a release build
            self.cfg.update('configopts', "-DCMAKE_BUILD_TYPE=Release")

            # prefer static libraries, if available
            if self.toolchain.options.get('dynamic', False):
                self.cfg.update('configopts', "-DGMX_PREFER_STATIC_LIBS=OFF")
            else:
                self.cfg.update('configopts', "-DGMX_PREFER_STATIC_LIBS=ON")

            # always specify to use external BLAS/LAPACK
            self.cfg.update('configopts', "-DGMX_EXTERNAL_BLAS=ON -DGMX_EXTERNAL_LAPACK=ON")

            # disable GUI tools
            self.cfg.update('configopts', "-DGMX_X11=OFF")

            # set regression test path
            prefix = 'regressiontests'
            if any([src['name'].startswith(prefix) for src in self.src]):
                major_minor_version = '.'.join(self.version.split('.')[:2])
                self.cfg.update('configopts', "-DREGRESSIONTEST_PATH='%%(builddir)s/%s-%%(version)s' " % prefix)

            # enable OpenMP support if desired
            if self.toolchain.options.get('openmp', None):
                self.cfg.update('configopts', "-DGMX_OPENMP=ON")
            else:
                self.cfg.update('configopts', "-DGMX_OPENMP=OFF")

            # Disable MPI support (for initial, serial/SMP build)
            self.cfg.update('configopts', "-DGMX_MPI=OFF")

            # explicitly disable GPU support if CUDA is not available,
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
                # This may not work in all versions of GROMACS post 4.6.
                for libname in ['BLAS', 'LAPACK']:
                    lib_dir = os.getenv('%s_LIB_DIR' % libname)
                    libs = os.getenv('LIB%s' % libname)
                    if self.toolchain.toolchain_family() == toolchain.CRAYPE:
                        self.cfg.update('configopts', '-DGMX_%s_USER="%s/libsci_gnu_mpi_mp.a"' % (libname, lib_dir))
                    else:
                        libfile = "lib" + libs.split('-l')[1].rstrip() + ".so"
                        libstr = os.path.join(lib_dir, libfile)
                        self.cfg.update('configopts', '-DGMX_%s_USER="%s"' % (libname, libstr))

            # no more GSL support in GROMACS 5.x, see http://redmine.gromacs.org/issues/1472
            if LooseVersion(self.version) < LooseVersion('5.0'):
                # enable GSL when it's provided
                if get_software_root('GSL'):
                    self.cfg.update('configopts', "-DGMX_GSL=ON")
                else:
                    self.cfg.update('configopts', "-DGMX_GSL=OFF")

            # set regression test path
            prefix = 'regressiontests'
            if any([src['name'].startswith(prefix) for src in self.src]):
                self.cfg.update('configopts', "-DREGRESSIONTEST_PATH='%%(builddir)s/%s-%%(version)s' " % prefix)

            # complete configuration with configure_method of parent
            self.cmake_objdir_normal = 'build-normal'
            os.mkdir(self.cmake_objdir_normal)
            os.chdir(self.cmake_objdir_normal)
            out = super(EB_GROMACS, self).configure_step(srcdir='..')

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

            os.chdir('..')

    def build_step(self):

        if LooseVersion(self.version) >= LooseVersion('4.6'):
            os.chdir(self.cmake_objdir_normal)
        else:
            self.cfg.update("prebuildopts", 'LIBS="${EBVARLIBLAPACK} ${LIBS}"')

        super(EB_GROMACS, self).build_step()

        if LooseVersion(self.version) >= LooseVersion('4.6'):
            os.chdir('..')

    def test_step(self):
        """Run the basic tests (but not necessarily the full regression tests)
           using make check"""
        # allow to escape testing by setting runtest to False
        if not self.cfg['runtest'] and not isinstance(self.cfg['runtest'], bool):
            self.cfg['runtest'] = 'check'
            # make very sure OMP_NUM_THREADS is set to 1, to avoid hanging GROMACS regression test
            env.setvar('OMP_NUM_THREADS', '1')
            if LooseVersion(self.version) >= LooseVersion('4.6'):
                os.chdir(self.cmake_objdir_normal)
            else:
                self.cfg['runtest'] = 'LIBS="${EBVARLIBLAPACK} ${LIBS}" check'
            super(EB_GROMACS, self).test_step()
            if LooseVersion(self.version) >= LooseVersion('4.6'):
                os.chdir('..')

    def install_step(self):
        """Custom install step for GROMACS; figure out where libraries were installed to.
           Also, install the MPI version of the executable in a separate step."""
        if LooseVersion(self.version) >= LooseVersion('4.6'):
            os.chdir(self.cmake_objdir_normal)
        super(EB_GROMACS, self).install_step()
        if LooseVersion(self.version) >= LooseVersion('4.6'):
            os.chdir('..')

        # the GROMACS libraries get installed in different locations (deeper subdirectory), depending on the platform;
        # this is determined by the GNUInstallDirs CMake module;
        # rather than trying to replicate the logic, we just figure out where the library was placed

        if self.toolchain.options.get('dynamic', False):
            self.libext = get_shared_lib_ext()
        else:
            self.libext = 'a'

        if LooseVersion(self.version) < LooseVersion('5.0'):
            libname = 'libgmx*.%s' % self.libext
        else:
            libname = 'libgromacs*.%s' % self.libext

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

        # Install a version with the MPI suffix
        if self.toolchain.options.get('usempi', None):
            if LooseVersion(self.version) < LooseVersion('4.6'):
                cmd = "make distclean"
                (out, _) = run_cmd(cmd, log_all=True, simple=False)
                self.cfg.update('configopts', "--enable-mpi --program-suffix={0}".format(self.cfg['mpisuffix']))
                ConfigureMake.configure_step(self)
                self.cfg.update("buildopts", "mdrun")
                super(EB_GROMACS, self).build_step()
                cmd = "%s make install-mdrun %s" % (self.cfg['preinstallopts'], self.cfg['installopts'])
                (out, _) = run_cmd(cmd, log_all=True, simple=False)
            else:
                cmake_objdir = "build-mdrun-only"
                os.mkdir(cmake_objdir)
                os.chdir(cmake_objdir)
                self.cfg['configopts'] = re.sub(r'-DGMX_MPI=OFF', r'', self.cfg['configopts'])
                if self.cfg['mpi_numprocs'] == 0:
                    self.log.info("No specific number of test MPI tasks requested -- using parallelism ({0})".format(self.cfg['parallel']))
                    self.cfg['mpi_numprocs'] = self.cfg['parallel']
                elif self.cfg['mpi_numprocs'] > self.cfg['parallel']:
                    self.log.warning("Number of test MPI tasks ({0}) is greater than parallelism ({1})".format(self.cfg['mpi_numprocs'], self.cfg['parallel']))
                self.cfg.update('configopts', "-DGMX_MPI=ON -DGMX_THREAD_MPI=OFF -DMPIEXEC={0} -DMPIEXEC_NUMPROC_FLAG={1} -DNUMPROC={2} -DGMX_BUILD_MDRUN_ONLY=ON".format(self.cfg['mpiexec'], self.cfg['mpiexec_numproc_flag'], self.cfg['mpi_numprocs']))
                self.log.info("Using {0} as MPI executable when testing, with numprocs flag \"{1}\" and {2} tasks".format(self.cfg['mpiexec'], self.cfg['mpiexec_numproc_flag'], self.cfg['mpi_numprocs']))

                # Rebuild with MPI options
                super(EB_GROMACS, self).configure_step(srcdir='..')
                super(EB_GROMACS, self).build_step()
                super(EB_GROMACS, self).install_step()
                os.chdir('..')

                self.log.info("A full regression test suite is available from the GROMACS web site")

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

        # Add the _d suffix to the suffix, in case of the double precission
        if '-DGMX_DOUBLE=on' in self.cfg['configopts']:
            suff = suff + '_d'
        elif '-DGMX_DOUBLE=ON' in self.cfg['configopts']:
            suff = suff + '_d'

        dirs = [os.path.join('include', 'gromacs')]

        # in GROMACS v5.1, only 'gmx' binary is there
        # (only) in GROMACS v5.0, other binaries are symlinks to 'gmx'
        binaries = []
        libnames = []
        if LooseVersion(self.version) < LooseVersion('5.1'):
            binaries.extend(['editconf', 'g_lie', 'genbox', 'genconf', 'mdrun'])

        if LooseVersion(self.version) >= LooseVersion('5.0'):
            binaries.append('gmx')
            libnames.append('gromacs')
            if self.toolchain.options.get('usempi', None):
                binaries.append('mdrun{0}'.format(suff))
        else:
            libnames.extend(['gmxana', 'gmx', 'md'])
            # I don't know when the gmxpreprocess library was introduced.
            # This LooseVersion number may have to be tweaked.
            if LooseVersion(self.version) > LooseVersion('3.3.3'):
                libnames.append('gmxpreprocess')
            if self.toolchain.options.get('usempi', None):
                libnames.extend(['{0}{1}'.format(libname, suff) for libname in libnames])

        libs = ['lib%s%s.%s' % (libname, suff, self.libext) for libname in libnames]

        # I don't know when the pkgconfig directory was introduced.
        # This LooseVersion number may have to be tweaked.
        if LooseVersion(self.version) > LooseVersion('3.3.3'):
            dirs.append(os.path.join(self.lib_subdir, "pkgconfig"))

        custom_paths = {
            'files': ['bin/%s' % binary for binary in binaries] +
                     [os.path.join(self.lib_subdir, lib) for lib in libs],
            'dirs': dirs
        }

        super(EB_GROMACS, self).sanity_check_step(custom_paths=custom_paths)
