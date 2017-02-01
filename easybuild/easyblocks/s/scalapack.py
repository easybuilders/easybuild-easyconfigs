##
# Copyright 2009-2017 Ghent University
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
EasyBuild support for building and installing ScaLAPACK, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import glob
import os
from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.blacs import det_interface  #@UnresolvedImport
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.toolchains.linalg.acml import Acml
from easybuild.toolchains.linalg.atlas import Atlas
from easybuild.toolchains.linalg.blacs import Blacs
from easybuild.toolchains.linalg.gotoblas import GotoBLAS
from easybuild.toolchains.linalg.lapack import Lapack
from easybuild.toolchains.linalg.openblas import OpenBLAS
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import copy_file
from easybuild.tools.modules import get_software_root


class EB_ScaLAPACK(ConfigureMake):
    """
    Support for building and installing ScaLAPACK, both versions 1.x and 2.x
    """

    def configure_step(self):
        """Configure ScaLAPACK build by copying SLmake.inc.example to SLmake.inc and checking dependencies."""

        src = os.path.join(self.cfg['start_dir'], 'SLmake.inc.example')
        dest = os.path.join(self.cfg['start_dir'], 'SLmake.inc')

        if os.path.exists(dest):
            raise EasyBuildError("Destination file %s exists", dest)
        else:
            copy_file(src, dest)

        self.loosever = LooseVersion(self.version)

    def build_step(self):
        """Build ScaLAPACK using make after setting make options."""

        # MPI compiler commands
        known_mpi_libs = [toolchain.MPICH, toolchain.MPICH2, toolchain.MVAPICH2]  #@UndefinedVariable
        known_mpi_libs += [toolchain.OPENMPI, toolchain.QLOGICMPI]  #@UndefinedVariable
        if os.getenv('MPICC') and os.getenv('MPIF77') and os.getenv('MPIF90'):
            mpicc = os.getenv('MPICC')
            mpif77 = os.getenv('MPIF77')
            mpif90 = os.getenv('MPIF90')
        elif self.toolchain.mpi_family() in known_mpi_libs:
            mpicc = 'mpicc'
            mpif77 = 'mpif77'
            mpif90 = 'mpif90'
        else:
            raise EasyBuildError("Don't know which compiler commands to use.")

        # determine build options BLAS and LAPACK libs
        extra_makeopts = []

        acml = get_software_root(Acml.LAPACK_MODULE_NAME[0])
        lapack = get_software_root(Lapack.LAPACK_MODULE_NAME[0])
        openblas = get_software_root(OpenBLAS.LAPACK_MODULE_NAME[0])

        if lapack:
            extra_makeopts.append('LAPACKLIB=%s' % os.path.join(lapack, 'lib', 'liblapack.a'))

            for blas in [Atlas, GotoBLAS]:
                blas_root = get_software_root(blas.BLAS_MODULE_NAME[0])
                if blas_root:
                    blas_libs = ' '.join(['-l%s' % lib for lib in blas.BLAS_LIB])
                    extra_makeopts.append('BLASLIB="-L%s %s -lpthread"' % (os.path.join(blas_root, 'lib'), blas_libs))
                    break

            if not blas_root:
                raise EasyBuildError("Failed to find a known BLAS library, don't know how to define 'BLASLIB'")

        elif acml:
            acml_base_dir = os.getenv('ACML_BASEDIR', 'NO_ACML_BASEDIR')
            acml_static_lib = os.path.join(acml, acml_base_dir, 'lib', 'libacml.a')
            extra_makeopts.extend([
                'BLASLIB="%s -lpthread"' % acml_static_lib,
                'LAPACKLIB=%s' % acml_static_lib
            ])
        elif openblas:
            libdir = os.path.join(openblas, 'lib')
            blas_libs = ' '.join(['-l%s' % lib for lib in OpenBLAS.BLAS_LIB])
            extra_makeopts.extend([
                'BLASLIB="-L%s %s -lpthread"' % (libdir, blas_libs),
                'LAPACKLIB="-L%s %s"' % (libdir, blas_libs),
            ])
        else:
            raise EasyBuildError("Unknown LAPACK library used, no idea how to set BLASLIB/LAPACKLIB make options")

        # build procedure changed in v2.0.0
        if self.loosever < LooseVersion('2.0.0'):

            blacs = get_software_root(Blacs.BLACS_MODULE_NAME[0])
            if not blacs:
                raise EasyBuildError("BLACS not available, yet required for ScaLAPACK version < 2.0.0")

            # determine interface
            interface = det_interface(self.log, os.path.join(blacs, 'bin'))

            # set build and BLACS dir correctly
            extra_makeopts.append('home=%s BLACSdir=%s' % (self.cfg['start_dir'], blacs))

            # set BLACS libs correctly
            blacs_libs = [
                ('BLACSFINIT', "F77init"),
                ('BLACSCINIT', "Cinit"),
                ('BLACSLIB', "")
            ]
            for (var, lib) in blacs_libs:
                extra_makeopts.append('%s=%s/lib/libblacs%s.a' % (var, blacs, lib))

            # set compilers and options
            noopt = ''
            if self.toolchain.options['noopt']:
                noopt += " -O0"
            if self.toolchain.options['pic']:
                noopt += " -fPIC"
            extra_makeopts += [
                'F77="%s"' % mpif77,
                'CC="%s"' % mpicc,
                'NOOPT="%s"' % noopt,
                'CCFLAGS="-O3 %s"' % os.getenv('CFLAGS')
            ]

            # set interface
            extra_makeopts.append("CDEFS='-D%s -DNO_IEEE $(USEMPI)'" % interface)

        else:

            # determine interface
            if self.toolchain.mpi_family() in known_mpi_libs:
                interface = 'Add_'
            else:
                raise EasyBuildError("Don't know which interface to pick for the MPI library being used.")

            # set compilers and options
            extra_makeopts += [
                'FC="%s"' % mpif90,
                'CC="%s"' % mpicc,
                'CCFLAGS="%s"' % os.getenv('CFLAGS'),
                'FCFLAGS="%s"' % os.getenv('FFLAGS'),
            ]

            # set interface
            extra_makeopts.append('CDEFS="-D%s"' % interface)

        # update make opts, and build_step
        self.cfg.update('buildopts', ' '.join(extra_makeopts))

        super(EB_ScaLAPACK, self).build_step()

    def install_step(self):
        """Install by copying files to install dir."""

        # include files and libraries
        path_info = [
            ('SRC', 'include', '.h'), # include files
            ('', 'lib', '.a'), # libraries
        ]
        for (srcdir, destdir, ext) in path_info:

            src = os.path.join(self.cfg['start_dir'], srcdir)
            dest = os.path.join(self.installdir, destdir)

            for lib in glob.glob(os.path.join(src, '*%s' % ext)):
                copy_file(lib, os.path.join(dest, os.path.basename(lib)))
                self.log.debug("Copied %s to %s" % (lib, dest))

    def sanity_check_step(self):
        """Custom sanity check for ScaLAPACK."""

        custom_paths = {
            'files': ["lib/libscalapack.a"],
            'dirs': []
        }

        super(EB_ScaLAPACK, self).sanity_check_step(custom_paths=custom_paths)
