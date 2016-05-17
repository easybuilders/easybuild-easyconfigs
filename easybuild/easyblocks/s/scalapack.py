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
EasyBuild support for building and installing ScaLAPACK, implemented as an easyblock

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""

import glob
import os
import shutil
from distutils.version import LooseVersion

import easybuild.tools.toolchain as toolchain
from easybuild.easyblocks.blacs import det_interface  #@UnresolvedImport
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.lapack import get_blas_lib as lapack_get_blas_lib  #@UnresolvedImport
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root


class EB_ScaLAPACK(ConfigureMake):
    """
    Support for building and installing ScaLAPACK, both versions 1.x and 2.x
    """

    def configure_step(self):
        """Configure ScaLAPACK build by copying SLmake.inc.example to SLmake.inc and checking dependencies."""

        src = os.path.join(self.cfg['start_dir'], 'SLmake.inc.example')
        dest = os.path.join(self.cfg['start_dir'], 'SLmake.inc')

        if not os.path.isfile(src):
            raise EasyBuildError("Can't fin source file %s", src)

        if os.path.exists(dest):
            raise EasyBuildError("Destination file %s exists", dest)

        try:
            shutil.copy(src, dest)
        except OSError, err:
            raise EasyBuildError("Symlinking %s to %s failed: %s", src, dest, err)

        self.loosever = LooseVersion(self.version)

        # make sure required dependencies are available
        deps = [("LAPACK", "ACML", "OpenBLAS")]
        self.log.deprecated("EB_ScaLAPACK.configure_step uses hardcoded list of LAPACK libs", '3.0')
        # BLACS is only a dependency for ScaLAPACK versions prior to v2.0.0
        if self.loosever < LooseVersion("2.0.0"):
            deps.append(("BLACS",))
        for depgrp in deps:
            ok = False
            for dep in depgrp:
                if get_software_root(dep):
                    ok = True
                    break
            if not ok:
                raise EasyBuildError("None of the following dependencies %s are available/loaded.", str(depgrp))

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

        # set BLAS and LAPACK libs
        extra_makeopts = None
        self.log.deprecated("EB_ScaLAPACK.build_step doesn't use toolchain support for BLAS/LAPACK libs", '3.0')
        if get_software_root('LAPACK'):
            extra_makeopts = [
                'BLASLIB="%s -lpthread"' % lapack_get_blas_lib(self.log),
                'LAPACKLIB=%s/lib/liblapack.a' % get_software_root('LAPACK')
            ]
        elif get_software_root('ACML'):
            root = get_software_root('ACML')
            acml_static_lib = os.path.join(root, os.getenv('ACML_BASEDIR', 'NO_ACML_BASEDIR'), 'lib', 'libacml.a')
            extra_makeopts = [
                'BLASLIB="%s -lpthread"' % acml_static_lib,
                'LAPACKLIB=%s' % acml_static_lib
            ]
        elif get_software_root('OpenBLAS'):
            root = get_software_root('OpenBLAS')
            extra_makeopts = [
                'BLASLIB="%s -lpthread"' % lapack_get_blas_lib(self.log),
                'LAPACKLIB="%s"' % lapack_get_blas_lib(self.log),
            ]
        else:
            raise EasyBuildError("LAPACK, ACML or OpenBLAS are not available, no idea how to set BLASLIB/LAPACKLIB make options.")

        # build procedure changed in v2.0.0
        if self.loosever < LooseVersion("2.0.0"):

            blacs = get_software_root('BLACS')

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
            ("SRC", "include", ".h"), # include files
            ("", "lib", ".a"), # libraries
        ]
        for (srcdir, destdir, ext) in path_info:

            src = os.path.join(self.cfg['start_dir'], srcdir)
            dest = os.path.join(self.installdir, destdir)

            try:
                os.makedirs(dest)
                os.chdir(src)

                for lib in glob.glob('*%s' % ext):

                    # copy file
                    shutil.copy2(os.path.join(src, lib), dest)

                    self.log.debug("Copied %s to %s" % (lib, dest))

            except OSError, err:
                raise EasyBuildError("Copying %s/*.%s to installation dir %s failed: %s", src, ext, dest, err)

    def sanity_check_step(self):
        """Custom sanity check for ScaLAPACK."""

        custom_paths = {
            'files': ["lib/libscalapack.a"],
            'dirs': []
        }

        super(EB_ScaLAPACK, self).sanity_check_step(custom_paths=custom_paths)
